from pymongo import Connection
from pymongo.errors import ConnectionFailure
import sys


if __name__ == "__main__":
	try:
		c = Connection(host="128.122.79.158", port=27011)
	except ConnectionFailure, e:
		sys.stderr.write("Could not connect to MongoDB: %s" % e)
		sys.exit(1)
	dbh = c["ItalianTweets"]
	assert dbh.connection == c
	dbh.authenticate("root", "zn9zabgy")

	collection = dbh["ItalianTweets"]

	print collection.count()

	data = collection.find({"random_number":{"$lt": 0.1, "$gt":0.0}}).limit(10000)
	f = open("italianelection.json", "w+")

	for d in data:
		f.write(str(d))

	