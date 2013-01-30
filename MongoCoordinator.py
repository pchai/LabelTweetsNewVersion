#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Peihong Chai on 2013-01-28.
# Copyright (c) , under the Simplified BSD License.
# For more information on FreeBSD see: http://www.opensource.org/licenses/bsd-license.php
# All rights reserved.
"""
import sys
from pymongo import Connection
from pymongo.errors import ConnectionFailure
from pymongo import ASCENDING
from pymongo import DESCENDING


from operator import itemgetter
import datetime

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
        if "members" not in self.dbh.collection_names():
            self.dbh.create_collection("members")
            print "Create Collection Members"
        collection = self.dbh["members"]
        user = collection.find_one({"email": email})
        if user == None:
            print "User not in database"
            return False
        return True

    def validate_signup(self, email):
        if "members" not in self.dbh.collection_names():
            self.dbh.create_collection("members")
            print "Create Collection Members"
        collection = self.dbh["members"]
        user = collection.find_one({"email": email})
        if user == None:
            return True
        else:
            return False


    def get_username(self, email):
        collection = self.dbh["members"]
        user = collection.find_one({"email": email})
        if not user:
            return "NoRecord"
        else:
            return user.get("user_name")

    def insert_login(self, email, user_name):
        if "members" not in self.dbh.collection_names():
            self.dbh.create_collection("members")
            print "Create Collection..."
        collection = self.dbh["members"]
        collection.save({"email": email, "user_name": user_name, "batch": {}})

    def get_batchs(self, skip_nr, batch):
        if batch not in self.dbh.collection_names():
            self.dbh.create_collection(batch)
            for i in range(1, 101):
                self.dbh[batch].insert({"batch": i, "owner": {}})
        collection = self.dbh[batch]
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
        if owner:
            return owner.get(user_name)
        else:
            return 0

    def add_batch(self, batch_nr, batch, email, collection):
        '''This method will update the database when you extract'''
        memberCollection = "members"
        batchCollection = batch
        collection_member = self.dbh[memberCollection]
        collection_batch = self.dbh[batchCollection]
        user = collection_member.find_one({"email": email})
        name = user.get("user_name")
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
            batch_list = batch_dict.get(collection)
            if batch_list:
                if batch_nr not in batch_list:
                    batch_list.append(batch_nr)
            else:
                batch_list = [batch_nr]
            collection_member.update({"email": email}, {"$set": {"batch." + collection: batch_list}}, safe=True)

    def update_label(self, tweet_id, option, batch_nr, tweet_nr, collection, batch, username):
        '''This method will upinsert the labelling of the tweet'''
        myCollection = collection
        batchCollection = batch
        collection = self.dbh[myCollection]
        collection_batch = self.dbh[batchCollection]
        result = collection.find_one({"id_str": tweet_id})
        if "label_option" in result:
            tweet = collection.find_one({"id_str": tweet_id})
            label_option = tweet.get("label_option")
            label_option.append(option)
            collection.update({"id_str": tweet_id}, {"$set": {"label_option": label_option}}, safe=True)
        else:
            collection.update({"id_str": tweet_id}, {"$set": {"label_option": [option]}}, safe=True)
        collection_batch.update({"batch": int(batch_nr)}, {"$set": {"owner."+username: int(tweet_nr)}}, safe=True)

    def new_survey(self, survey_name):
        if "survey" not in self.dbh.collection_names():
            self.dbh.create_collection("survey")
        print "Create Collection Survey"
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        if survey is not None:
            return False
        collection.save({"survey_name": survey_name}, safe=True)
        return True

    def exist_survey(self):
        if "survey" not in self.dbh.collection_names():
            self.dbh.create_collection("survey")
        print "Create Collection Survey"
        collection = self.dbh["survey"]
        data = collection.find()
        result = []
        for d in data:
            result.append(d.get("survey_name"))
        return result

    def get_survey(self, survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        survey["questions"] = sorted(survey["questions"], key=itemgetter('_id'))
        collection.save(survey, safe=True)
        return survey

    def update_survey(self, survey_name, question):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        flag = False
        for q in survey["questions"]:
            if q["_id"] == question["_id"]:
                survey["questions"][survey["questions"].index(q)] = question
                flag = True
        if flag:
            collection.save(survey, safe=True)
        else:
            collection.update({"survey_name": survey_name}, {"$push": {"questions": question}}, upsert=True, safe=True)

    def delete_survey(self, survey_name, question_nr):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name}, {"$pull": {"questions": {"_id": int(question_nr)}}})
        survey = collection.find_one({"survey_name": survey_name})
        flag = False
        for q in survey["questions"]:
            if q["_id"] > int(question_nr):
                survey["questions"][survey["questions"].index(q)]["_id"] -= 1
                flag = True
        if flag:
            collection.save(survey, safe=True)

    def move_survey(self, survey_name, question_nr, direction):
        collection = self.dbh["survey"]
        if direction == "up":
            survey = collection.find_one({"survey_name": survey_name})
            if int(question_nr) != 1:
                tmp = survey["questions"][int(question_nr)-2]["_id"]
                survey["questions"][int(question_nr)-2]["_id"] = survey["questions"][int(question_nr)-1]["_id"]
                survey["questions"][int(question_nr)-1]["_id"] = tmp
                collection.save(survey, safe=True)
        elif direction == "down":
            survey = collection.find_one({"survey_name": survey_name})
            if int(question_nr) != len(survey["questions"]):
                survey = collection.find_one({"survey_name": survey_name})
                tmp = survey["questions"][int(question_nr)-1]["_id"]
                survey["questions"][int(question_nr)-1]["_id"] = survey["questions"][int(question_nr)]["_id"]
                survey["questions"][int(question_nr)]["_id"] = tmp
                collection.save(survey, safe=True)

    def insert_survey_log(self, survey_log, user, msg):
        #Add log information about who edited the survey
        if survey_log not in self.dbh.collection_names():
            self.dbh.create_collection(survey_log)
        print "Create Collection Survey Log"
        collection = self.dbh[survey_log]
        now = str(datetime.datetime.now())
        doc = {"create_at": now, "user": user, "msg":msg}
        collection.save(doc, safe="true")

    def get_survey_log(self, survey_log):
        #Get all the survey log
        collection = self.dbh[survey_log]
        data = collection.find(sort=[("create_at", DESCENDING)]).limit(10)
        return data

