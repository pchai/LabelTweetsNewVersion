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
        print self.mongo
        self.dbh = self.mongo[self.database]
        self.dbh.authenticate("root", "zn9zabgy")


    def valid_login(self, email):
        collection = self.dbh["members"]
        user = None
        user = collection.find_one({"email": email})
        if user == None:
            print "User not in database"
            return False
        return True

    def validate_signup(self, email):
        collection = self.dbh["members"]
        user = None
        user = collection.find_one({"email": email})
        if user == None:
            return True
        else:
            return False


    def get_username(self, email):
        collection = self.dbh["members"]
        user = None
        user = collection.find_one({"email": email})
        if not user:
            return "NoRecord"
        else:
            return user.get("user_name")

    def insert_login(self, email, user_name):
        collection = self.dbh["members"]
        try:
            collection.save({"email": email, "user_name": user_name, "batch": {}})
            return True
        except:
            print "Unexpected error on insert_login:", sys.exc_info()[0]
            return False

    def get_batchs(self, skip_nr, batch, survey):
        collection = self.dbh[batch]
        collection_survey = self.dbh["survey"]
        survey = collection_survey.find_one({"survey_name": survey})
        if "fold" in survey:
            fold = int(survey["fold"])
        else:
            fold = 2
        try:
            batchs = collection.find(sort=[("batch", ASCENDING)]).skip(skip_nr * 10)
            allbatchs = collection.find(sort=[("batch", ASCENDING)])
            result = {"batch": [], "owner": [], "labeld": [], "dict": [], "fold":fold}
            for b in allbatchs:
                owner = b.get("owner")
                result["dict"].append(owner)
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
        except:
            print "Unexpected error on get_batchs:", sys.exc_info()[0]
            return {}

    def get_next_batch(self, batch, survey_name, username):
        collection_batch = self.dbh[batch]
        collection_survey = self.dbh["survey"]
        survey = collection_survey.find_one({"survey_name": survey_name})
        if "intercode" in survey:
            intercode = survey["intercode"]
        else:
            intercode = False
        if "fold" in survey:
            fold = int(survey["fold"])
        else:
            fold = 2
        try:
            batchs = collection_batch.find(sort=[("batch", ASCENDING)])
            print batchs
            for batch in batchs:
                if intercode:
                    if len(batch["owner"]) > 0 and len(batch["owner"]) < fold and username not in batch["owner"].keys():
                        return batch["batch"]
                else:
                    if len(batch["owner"]) == 0:
                        return batch["batch"]
        except:
            print "Unexpected error on get_next_batch:", sys.exc_info()[0]
            return {}

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
        try:
            label_counter = (batch_nr - 1) * 100 + tweet_nr
            tweet = collection.find_one({"label_counter": label_counter})
            result = {"id": "", "text": "", "label_counter": "", "user": "", "link": []}
            result["id"] = tweet.get("id_str")
            result["text"] = tweet.get("text")
            result["tweet_nr"] = str(tweet_nr)
            user = tweet.get("user")
            result["user"] = user["screen_name"]
            result["description"] = user["description"]
            entity = tweet.get("entities")
            urls = entity["urls"]
            for u in urls:
                result["link"].append(u["expanded_url"])
            return result
        except:
            print "Unexpected error on get_tweet:", sys.exc_info()[0]
            return {}


    def get_labelled(self, batch_nr, batch, user_name):
        myCollection = batch
        collection = self.dbh[myCollection]
        try:
            result = collection.find_one({"batch": int(batch_nr)})
            owner = result.get("owner")
            if owner:
                return owner.get(user_name)
            else:
                return 0
        except:
            print "Unexpected error on get_labelled:", sys.exc_info()[0]

    def add_batch(self, batch_nr, batch, email, collection):
        '''This method will update the database when you extract'''

        collection_member = self.dbh["members"]
        collection_batch = self.dbh[batch]
        try:
            user = collection_member.find_one({"email": email})
            name = user.get("user_name")
            doc = collection_batch.find_one({"batch": int(batch_nr)})
            owner = doc.get("owner")
            if name not in owner:
                owner[name] = 0
            collection_batch.update({"batch": int(batch_nr)}, {"$set": {"owner": owner}}, safe=True)
            if collection not in user.get("batch"):
                collection_member.update({"email": email}, {"$set": {"batch." + collection: []}}, safe=True)
            batch_dict = user.get("batch")
            batch_list = batch_dict.get(collection)
            if batch_list:
                if int(batch_nr) not in batch_list:
                    batch_list.append(int(batch_nr))
            else:
                batch_list = [int(batch_nr)]
            collection_member.update({"email": email}, {"$set": {"batch." + collection: batch_list}}, safe=True)
        except:
            print "Unexpected error on add_batch:", sys.exc_info()[0]
            return False
        return True

    def put_back_batch(self, batch_nr, batch, email, collection):
        collection_member = self.dbh["members"]
        collection_batch = self.dbh[batch]
        try:
            user = collection_member.find_one({"email": email})
            name = user.get("user_name")
            doc = collection_batch.find_one({"batch": int(batch_nr)})
            owner = doc.get("owner")
            if name in owner and owner[name] == 0:
                collection_batch.update({"batch": int(batch_nr)}, {"$unset": {"owner."+name: owner}}, safe=True)
            batch_dict = user.get("batch")
            batch_list = batch_dict.get(collection)
            if batch_list:
                if batch_nr in batch_list:
                    batch_list.remove(batch_nr)
            collection_member.update({"email": email}, {"$set": {"batch." + collection: batch_list}}, safe=True)
        except:
            print "Unexpected error on putback_batch:", sys.exc_info()[0]

    def update_intercode(self, survey_name, intercode, fold):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name},
            {"$set":{"intercode": intercode, "fold": fold}}, safe=True)



    def update_label(self, tweet_id, survey, batch_nr, tweet_nr, collection, batch, username):
        '''This method will upinsert the labelling of the tweet'''
        collection = self.dbh[collection]
        collection_batch = self.dbh[batch]
        result = collection.find_one({"id_str": tweet_id})
        if "label_option" in result:
	    collection.update({"id_str": tweet_id}, {"$push": {"label_option": {username:{"survey":survey}}}}, safe=True)
        else:
            collection.update({"id_str": tweet_id}, {"$set": {"label_option": [{username:{"survey":survey}}]}}, safe=True)
        collection_batch.update({"batch": int(batch_nr)}, {"$set": {"owner."+username: int(tweet_nr)}}, safe=True)

    def lock_survey(self, survey_name, bool_value):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name}, {"$set": {"lock" : bool_value}})

    def new_survey(self, survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        if survey:
            return False
        collection.save({"survey_name": survey_name}, safe=True)
        return True

    def drop_survey(self, survey_name):
        collection = self.dbh["survey"]
        collection.remove({"survey_name": survey_name})

    def exist_survey(self):
        collection = self.dbh["survey"]
        data = collection.find()
        result = []
        for d in data:
            result.append(d)
        return result

    def get_survey(self, survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        if "questions" in survey:
            survey["questions"] = sorted(survey["questions"], key=itemgetter('_id'))
            collection.save(survey, safe=True)
        return survey

    def get_admins(self):
        collection = self.dbh["survey"]
        survey = collection.find()
        admins = []
        for s in survey:
            admins.extend(s["admin"])
        return admins

    def update_survey(self, survey_name, question):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        flag = False
        if "questions" in survey:
            for q in survey["questions"]:
                index = survey["questions"].index(q)
                if q["_id"] == question["_id"]:
                    survey["questions"][index] = question
                    flag = True
        if flag:
            collection.save(survey, safe=True)
        else:
            collection.update({"survey_name": survey_name}, {"$push": {"questions": question}}, upsert=True, safe=True)

    def update_description(self, survey_name, description):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name}, {"$set":{"description": description}})

    def get_description(self, survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name":survey_name})
        return survey["description"]

    def get_random(self, survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        random_list = survey["random"] if "random" in survey else []
        return random_list

    def add_random(self, survey_name, block):
        collection = self.dbh["survey"]
        lst = block.split(",")
        collection.update({"survey_name": survey_name}, {"$push":{"random": lst}})

    def remove_random(self, survey_name):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name}, {"$unset":{"random": 1}})

    def delete_survey(self, survey_name, question_nr):
        collection = self.dbh["survey"]
        collection.update({"survey_name": survey_name}, {"$pull": {"questions": {"_id": int(question_nr)}}})
        survey = collection.find_one({"survey_name": survey_name})
        flag = False
        for q in survey["questions"]:
            index = survey["questions"].index(q)
            if q["_id"] > int(question_nr):
                survey["questions"][index]["_id"] -= 1
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
                tmp = survey["questions"][int(question_nr)-1]["_id"]
                survey["questions"][int(question_nr)-1]["_id"] = survey["questions"][int(question_nr)]["_id"]
                survey["questions"][int(question_nr)]["_id"] = tmp
                collection.save(survey, safe=True)

    def insert_survey_question(self, survey_name, question_nr, question):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": survey_name})
        if "questions" in survey:
            for q in survey["questions"]:
                if q["_id"] >= int(question_nr):
                    q["_id"] = int(q["_id"]) + 1
            collection.save(survey, safe=True)
            collection.update({"survey_name": survey_name}, {"$push": {"questions": question}}, upsert=True, safe=True)

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
        if survey_log not in self.dbh.collection_names():
            self.dbh.create_collection(survey_log)
            print "Create Collection Survey Log"
        collection = self.dbh[survey_log]
        data = collection.find(sort=[("create_at", DESCENDING)]).limit(10)
        return data

    def load_survey(self, survey_name, load_survey_name):
        collection = self.dbh["survey"]
        survey = collection.find_one({"survey_name": load_survey_name})
        if "questions" in survey:
            questions = survey["questions"]
            collection.update({"survey_name": survey_name}, {"$set":{"questions":questions}})





