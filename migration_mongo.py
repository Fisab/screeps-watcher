import pymongo
from watcher.config import Config

CONFIG = Config(config_path='config.yml')
MONGO_URL = f'mongodb://{CONFIG.db_secrets.user}:{CONFIG.db_secrets.password}@{CONFIG.db_secrets.host}:{CONFIG.db_secrets.port}'

print('Connection to mongo...')
client = pymongo.MongoClient(MONGO_URL)

print('Creating db...')
db = client[CONFIG.db_name]

print('Creating collections')
for collection in CONFIG.db_collections['expire_collections']:
	db[collection].create_index('_expire', expireAfterSeconds=CONFIG.db_expire)
	db[collection].create_index('tick', unique=True)
	print(f'\t- Created expire collection "{collection}"')
print()
for collection in CONFIG.db_collections['static_collections']:
	db[collection]
	print(f'\t- Created static collection "{collection}"')
print()
for collection in CONFIG.db_collections['custom_collections']:
	collection_name = list(collection.keys())[0]
	if 'uniq_index' in collection[collection_name]:
		db[collection_name].create_index(collection[collection_name]['uniq_index'], unique=True)
		print(f'\t- Created custom collection "{collection_name}" with uniq_index="{collection[collection_name]["uniq_index"]}"')
	else:
		db[collection_name]
		print(f'\t- Created custom collection "{collection_name}"')
