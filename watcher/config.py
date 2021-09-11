import yaml
from collections import namedtuple


class Config:
	_screeps_secrets = namedtuple('ScreepsSecrets', ['user', 'password'])
	_db_secrets = namedtuple('DBSecrets', ['host', 'port', 'user', 'password'])
	
	def __init__(self, config_path='../config.yml'):
		with open(config_path, 'r') as f:
			self.config = yaml.load(f, Loader=yaml.FullLoader)

	@property
	def screeps_secrets(self):
		return self._screeps_secrets(**self.config['screeps_secrets'])

	@property
	def db_secrets(self):
		return self._db_secrets(**self.config['db']['credentials'])

	@property
	def db_name(self):
		return self.config['db']['name']

	@property
	def db_collections(self):
		return {
			'expire_collections': self.config['db']['expire_collections'],
			'static_collections': self.config['db']['static_collections'],
			'custom_collections': self.config['db']['custom_collections'],
		}

	@property
	def db_expire(self):
		return self.config['db']['expireAfter']

	@property
	def shard(self):
		return f"shard{self.config['shard']}"


	