import logging

from pymongo import MongoClient, errors
from config import Config
from datetime import datetime


class Mongo:
	def __init__(self, host: str, port: int, user: str, password: str, db: str, config: Config):
		self.mongo_url = f"mongodb://{user}:{password}@{host}:{port}"
		self.client = None

		self.db_name = db
		self.config = config
		self._collections = None

	def connect(self):
		if not self.client:
			self.client = MongoClient(self.mongo_url)

	def _get_collections(self):
		if not self._collections:
			self._collections = self.client[self.db_name].list_collection_names()
		return self._collections

	def _create_new_collection(self, collection_name: str):
		db = self.client[self.db_name]
		db[collection_name].create_index('_expire', expireAfterSeconds=self.config.db_expire)
		db[collection_name].create_index('tick', unique=True)

	def _insert_one(self, collection: str, doc: dict):
		"""
		:param collection: name of collection
		:param doc: dict for insertion
		:return:
		"""
		if collection not in self._get_collections():
			logging.info(f'Creating new collection with name "{collection}"')
			self._create_new_collection(collection)
			self._collections.append(collection)
		try:
			self.client[self.db_name][collection].insert_one(doc)
		except errors.DuplicateKeyError:
			pass

	def get_subscribe_rooms(self):
		collection = self.client[self.db_name]['rooms_subscribe']
		cursor = collection.find()
		return [row['room_name'] for row in cursor]

	def upload_base(self, collection_name: str, message: dict):
		doc = {
			'_expire': datetime.utcnow(),
			**message
		}
		self._insert_one(collection_name, doc)


