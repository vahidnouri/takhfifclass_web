from os import getenv

#databases
LOCAL_MONGO_URI = 'mongodb://127.0.0.1:27017/takhfif_class?authSource=admin'
MONGO_URI = getenv('MONGODB_URI', default=LOCAL_MONGO_URI)
MONGODB_SETTINGS = dict(host=MONGO_URI)
