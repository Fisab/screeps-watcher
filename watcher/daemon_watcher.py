from config import Config
from screeps import Screeps, ScreepsWS
from db import Mongo
import logging

logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s %(message)s: (%(filename)s).%(funcName)s (%(lineno)d)'
)

config = Config()

mongo = Mongo(
	config.db_secrets.host,
	config.db_secrets.port,
	config.db_secrets.user,
	config.db_secrets.password,
	config.db_name,
	config
)
mongo.connect()

screeps = Screeps(config.shard)
screeps.init(config.screeps_secrets)

ws = ScreepsWS(
	config.screeps_secrets.user,
	config.screeps_secrets.password,
	shard=config.shard,
	mongo=mongo,
	api=screeps
)
ws.connect()
