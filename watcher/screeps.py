import json
import copy
from collections import namedtuple
from websocket import WebSocketApp
from db import Mongo
import screepsapi
import logging
import traceback

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s %(message)s: (%(filename)s).%(funcName)s (%(lineno)d)'
)


class ScreepsWS(screepsapi.Socket):
	def __init__(self, *args, shard: str, mongo: Mongo, api: 'Screeps'):
		super().__init__(*args, logging=True)

		self.mongo = mongo
		self.api = api
		self.shard = shard
		self.rooms_subscribe = []
		self._init_room = {}

		self.watcher_ticker = 0

	def subscribe_room(self, room_name: str):
		topic = f'room:{self.shard}/{room_name}'
		logging.info(f'Subscribing to "{topic}"')
		self.subscribe(topic)

	def unsubscribe(self, watchpoint: str):
		# и почему только в библиотеке это не реализовано?
		logging.info(f'Unsubscribing from "{watchpoint}"')
		self.ws.send('unsubscribe ' + watchpoint)

	def set_subscriptions(self):
		logging.info('Subscribing to "resources"')
		self.subscribe_user('resources')

		logging.info('Subscribing to "cpu"')
		self.subscribe_user('cpu')

		# кажется что это личные сообщения
		# logging.info('Subscribing to "newMessage"')
		# self.subscribe_user('newMessage')

		for room_subscribe in self.rooms_subscribe:
			self.subscribe_room(room_subscribe)

	@staticmethod
	def _merge_objects(init_obj, updates_obj, update_part):
		if isinstance(updates_obj[update_part], int):
			init_obj['tick'] = updates_obj[update_part]
			return init_obj
		for object_key in updates_obj[update_part].keys():
			# удаляем неактуальные данные
			if updates_obj[update_part][object_key] is None:
				# объект здох/ушел/...
				del init_obj[update_part][object_key]
			# добавляем новые данные
			elif object_key not in init_obj[update_part]:
				init_obj[update_part][object_key] = updates_obj[update_part][object_key]
			# обновляем существующие данные
			else:
				if isinstance(updates_obj[update_part][object_key], str):
					init_obj[update_part][object_key] = updates_obj[update_part][object_key]
				else:
					for key in updates_obj[update_part][object_key].keys():
						init_obj[update_part][object_key][key] = updates_obj[update_part][object_key][key]
		return init_obj

	def process_room(self, meta: str, meta_info: str, topic: str, data: dict):
		_update_parts = ['objects', 'users', 'flags', 'info', 'gameTime']
		room_name = topic
		if 'decorations' in data:
			del data['decorations']
		if room_name not in self._init_room:
			self._init_room[room_name] = data
			return
		else:
			room_copy = copy.deepcopy(self._init_room[room_name])
			for part in _update_parts:
				try:
					if part in data:
						self._merge_objects(room_copy, data, update_part=part)
				except Exception as e:
					print(traceback.format_exc())
					print('error:', e, part, data[part])
			self._init_room[room_name] = room_copy

		collection_name = f'{meta}:{meta_info}'
		self.mongo.upload_base(
			collection_name,
			{
				'room_name': room_name,
				**self._init_room[room_name]
			}
		)

	def process_basic(self, meta: str, meta_info: str, topic: str, data: dict, tick: int):
		doc = {
			'tick': tick,
			'meta': meta,
			'meta_info': meta_info,
			'message': data
		}
		collection_name = f'{meta}:{topic}'
		self.mongo.upload_base(collection_name, doc)

		# каждый 300-тый запрос проверяем не нужно ли отписаться от чего-то
		if self.watcher_ticker % 300 or len(self.rooms_subscribe) == 0:
			# проверяем - не нужно ли подписаться на новую комнату, или отписаться от какой?
			to_subscribe_rooms = self.mongo.get_subscribe_rooms()
			# проверяем нужно ли подписаться на новые
			for room in to_subscribe_rooms:
				if room not in self.rooms_subscribe:
					self.subscribe_room(room)
					# TODO: надо добавить сюда тики
					# room_status = self.api.room_overview(room)
					# self.mongo.upload_base('room_status', room_status)
					room_terrain = self.api.room_terrain(room)
					self.mongo.upload_base('room_terrain', room_terrain)

			# проверяем нужно ли отписаться от старых
			for room in self.rooms_subscribe:
				if room not in to_subscribe_rooms:
					watchpoint = f'room:{self.shard}/room"'
					self.unsubscribe(watchpoint)
			self.rooms_subscribe = to_subscribe_rooms

			self.watcher_ticker += 1

	def process_message(self, ws: WebSocketApp, message: str):
		try:
			data = json.loads(message)
		except Exception as e:
			logging.warning(f'Got "message" in strange format: {message}, error: {e}')
			return
		topic, data = data

		# Примеры топика и как я его паршу
		# room:shard0/W16N58
		# user:55d1c722bbc786b40f59ecc1/resources
		# {meta}:{meta_info}/{topic}
		meta, topic = topic.split('/')
		meta, meta_info = meta.split(':')

		if meta == 'user':
			game_tick = self.api.get_time()
			self.process_basic(meta, meta_info, topic, data, game_tick)
		else:
			self.process_room(meta, meta_info, topic, data)


class Screeps:
	def __init__(self, shard):
		self.shard = shard
		self.api = None

		self._my_rooms = None
		self.me = None

	def init(self, screeps_secrets: namedtuple):
		if not self.api:
			self.api = screepsapi.API(
				screeps_secrets.user,
				screeps_secrets.password
			)
		self.me = self.api.me()

	@property
	def my_rooms(self):
		if not self._my_rooms:
			self.update_my_rooms()
		return self._my_rooms

	def update_my_rooms(self):
		response = self.api.user_rooms(self.me['_id'])
		self._my_rooms = response['shards'][self.shard]

	def room_overview(self, room):
		return self.api.room_overview(room)

	def room_terrain(self, room):
		return self.api.room_terrain(room)

	def get_time(self):
		return self.api.time()
