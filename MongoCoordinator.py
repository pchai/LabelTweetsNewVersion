import sys

from pymongo import Connection
from pymongo.errors import ConnectionFailure
from pymongo import ASCENDING


class MongoDBCoordinator:
    """This class deal with the interaction of the
    webserver with MongoDB"""
    def __init__(self, host, database, port):
        self.database = database
        self.port = port
        self.host = host
        try:
            self.mongo = Connection(self.host, self.port)
        except ConnectionFailure, e:
            sys.stderr.write("Could not connect to MongoDB: %s" % e)

        self.dbh = self.mongo[self.database]
        self.dbh.authenticate("root", "zn9zabgy")

    def valid_login(self, email):
        myCollection = "members"
        if myCollection not in self.dbh.collection_names():
            self.dbh.create_collection(myCollection)
            print "Create Collection..."
        collection = self.dbh[myCollection]
        user = collection.find_one({"email": email})
        if not user:
            return "NoRecord"
        else:
            return user.get("email")

    def get_username(self, email):
        myCollection = "members"
        if myCollection not in self.dbh.collection_names():
            self.dbh.create_collection(myCollection)
            print "Create Collection..."
        collection = self.dbh[myCollection]
        user = collection.find_one({"email": email})
        if not user:
            return "NoRecord"
        else:
            return user.get("user_name")

    def insert_login(self, email, user_name):
        myCollection = "members"
        if myCollection not in self.dbh.collection_names():
            self.dbh.create_collection(myCollection)
            print "Create Collection..."
        collection = self.dbh[myCollection]
        collection.save({"email": email, "user_name": user_name, "batch": {}})

    def get_batchs(self, skip_nr, batch):
        myCollection = batch
        if myCollection not in self.dbh.collection_names():
            self.dbh.create_collection(myCollection)
            for i in range(1, 101):
                self.dbh[myCollection].insert({"batch": i, "owner": {}})
        collection = self.dbh[myCollection]
        batchs = collection.find(sort=[("batch", ASCENDING)]).skip(skip_nr * 20)
        allbatchs = collection.find(sort=[("batch", ASCENDING)])
        result = {"batch": [], "owner": [], "labeld": [], "dict": [], "sampling": 0}
        sampling = 0
        for b in allbatchs:
            owner = b.get("owner")
            result["dict"].append(owner)
            if len(owner.keys()) == 2:
                sampling = sampling + 1
        result["sampling"] = sampling
        for b in batchs:
            owner = b.get("owner")
            l1 = []
            l2 = []
            for k in owner.keys():
                l1.append(k)
                l2.append(owner[k])
            result["batch"].append(b.get("batch"))
            result["owner"].append(l1)
            result["labeld"].append(l2)
        print result
        return result

    def get_pull_batch(self, email, collection_name):
        '''This method will return all the batchs that this user has already pulled'''
        myCollection = "members"
        collection = self.dbh[myCollection]
        user = collection.find_one({"email": email})
        batch_dict = user.get("batch")
        if collection_name in batch_dict:
            batch_list = batch_dict[collection_name]
            batch_list.sort()
        else:
            batch_list = []
        return batch_list

    def get_tweet(self, batch_nr, tweet_nr, collection_name):
        myCollection = collection_name
        collection = self.dbh[myCollection]
        label_counter = (batch_nr - 1) * 100 + tweet_nr
        tweets = collection.find({"label_counter": label_counter})
        result = {"id": "", "text": "", "label_counter": "", "user": "", "link": []}
        for tweet in tweets:
            result["id"] = tweet.get("id_str")
            result["text"] = tweet.get("text")
            result["tweet_nr"] = str(tweet_nr)
            user = tweet.get("user")
            result["user"] = user["screen_name"]
            entity = tweet.get("entities")
            urls = entity["urls"]
            for u in urls:
                result["link"].append(u["expanded_url"])
        return result

    def get_labelled(self, batch_nr, batch, user_name):
        myCollection = batch
        collection = self.dbh[myCollection]
        result = collection.find_one({"batch": int(batch_nr)})
        owner = result.get("owner")
        return owner.get(user_name)

    def add_batch(self, batch_nr, batch, email, collection):
        '''This method will update the database when you extract'''
        memberCollection = "members"
        batchCollection = batch
        collection_member = self.dbh[memberCollection]
        collection_batch = self.dbh[batchCollection]
        user = collection_member.find_one({"email": email})
        name = user.get("user_name")
        print batch_nr
        doc = collection_batch.find_one({"batch": int(batch_nr)})
        owner = doc["owner"]
        if name not in owner:
            owner[name] = 0
        collection_batch.update({"batch": int(batch_nr)}, {"$set": {"owner": owner}}, safe=True)
        if not user:
            return "Couldn't add"
        else:
            if collection not in user.get("batch"):
                collection_member.update({"email": email}, {"$set": {"batch." + collection: []}}, safe=True)
            batch_dict = user.get("batch")
            batch_list = batch_dict[collection]
            if batch_nr not in batch_list:
                batch_list.append(batch_nr)
            collection_member.update({"email": email}, {"$set": {"batch." + collection: batch_list}}, safe=True)

    def update_label(self, tweet_id, option, batch_nr, tweet_nr, collection, batch, username):
        '''This method will upinsert the labelling of the tweet'''
        myCollection = collection
        batchCollection = batch
        collection = self.dbh[myCollection]
        collection_batch = self.dbh[batchCollection]
        result = collection.find_one({"id_str": tweet_id})
        print result
        if "label_option" in result:
            print "Option in result"
            collection.update({"id_str": tweet_id}, {"$set": {"label_option_extra": option}}, safe=True)
        else:
            print "Option not in result"
            collection.update({"id_str": tweet_id}, {"$set": {"label_option": option}}, safe=True)
        collection_batch.update({"batch": int(batch_nr)}, {"$set": {"owner."+username: int(tweet_nr)}}, safe=True)

