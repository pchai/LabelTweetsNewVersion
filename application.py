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

from flask import Flask
from flask import render_template
from flask import session, redirect, url_for, escape, request
from MongoCoordinator import MongoDBCoordinator

app = Flask(__name__)
tweets_per_batch = 100   #This is the number of tweets per batch

@app.route("/")
def hello():
    return render_template('hello.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == "POST":
        try:
            if mongo.validate_signup(escape(request.form["emailSignup"])):
                if not mongo.insert_login(request.form["emailSignup"], request.form["userName"]):
                    return render_template("error.html", msg="Internal Error")
                session['username'] = request.form["emailSignup"]
                result = mongo.exist_survey()
                return render_template("select.html", result=result)
            else:
                return render_template("error.html", msg="You have got a email address registered, go back and login using your email address")
        except KeyError:
                return render_template("error.html", msg="Bad Operation! You have to fill in your email address and username")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        try:
            if mongo.valid_login(request.form["emailSignin"]):
                session['username'] = request.form["emailSignin"]
                result = mongo.exist_survey()
                return render_template("select.html", result=result)
            else:
                return render_template("error.html", msg="No record exists, go back an signup")
        except KeyError:
            return render_template("error.html", msg="Bad Operation! You have to fill in your email address")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('hello'))

@app.route("/select", methods=['POST', 'GET'])
def select():
    if request.method == "POST":
        try:
            if request.form["survey"] == "Gun Control":
                return redirect(url_for('gun_mainpage'))
        except KeyError:
            return render_template("error.html", msg="Bad Request! You should select an option")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/gun_control/mainpage/", defaults={'page': 1})
@app.route("/gun_control/mainpage/<int:page>")
def gun_mainpage(page):
    if 'username' in session:
        username = mongo.get_username(session['username'])
        result = mongo.get_batchs(skip_nr=page - 1, batch="gunbatch")
        if not result:
            return render_template("error.html", msg="Internal Error")
        batchs = mongo.get_pull_batch(session['username'], "guncontrol")
        survey = mongo.get_survey("Gun Control")
        description = survey["description"] if "description" in survey else ""
        lock = survey["lock"] if "lock" in survey else ""
        return render_template("main.html", username=username, result=result, page=page, batchs=batchs, description=description, lock=lock)
    else:
        return render_template("main.html")


@app.route("/gun_control/pull", methods=['POST', 'GET'])
def gun_pull():
    if request.method == "POST":
        try:
            if 'username' in session:
                email = session['username']
                if "pull" in request.form and request.form["pull"]:
                    batch_nr = request.form["pull"]
                    mongo.add_batch(batch_nr, "gunbatch", email, "guncontrol")
                    return redirect(url_for('gun_mainpage'))
            else:
                return render_template("error.html", msg="You are not logged in")
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to pull a batch before confirming")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/gun_control/startconding", methods=['POST', 'GET'])
def start_coding():
    if request.method == "POST":
        try:
            survey = mongo.get_survey("Gun Control")
            questions = survey["questions"] if "questions" in survey else []
            collection_batch_name = "gunbatch" #The name of a mongodb collection of documents of batchs
            collection_tweet_name = "guncontrol" #The name of a mongodb collection of documents of tweets
            if 'username' in session:
                username = mongo.get_username(session['username'])
            else:
                return render_template("label.html")
            if request.form["submit"] == "Start coding":
                #Enter where you left last time
                batch = request.form["pull_batch"]
                tweet_nr = mongo.get_labelled(batch, collection_batch_name, username)
                if tweet_nr == tweets_per_batch:
                    return render_template("error.html", msg="Finished Batch! All the tweets in this batch has been labelled")
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, collection_tweet_name)
                if not result:
                    return render_template("error.html", msg="Internal Error")
                return render_template("label.html", batch=batch, username=escape(username), result=result, tweet_nr=tweet_nr, questions=questions)
            elif request.form["submit"] == "Put Back":
                batch = request.form["pull_batch"]
                tweet_nr = mongo.get_labelled(batch, collection_batch_name, username)
                if tweet_nr == 0:
                    mongo.put_back_batch(batch, "gunbatch", session['username'], "guncontrol")
                    return redirect(url_for('gun_mainpage'))
                else:
                    return render_template("error.html", msg="Couldn't put it back since you have already labelled this batch")
        except KeyError:
            return render_template("error.html", msg="Bad Request!")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/gun_control/links", methods=['POST', 'GET'])
def gun_links():
    if request.method == "POST":
        try:
            if request.form["appendlink"]:
                link = request.form["appendlink"]
                return render_template("link.html", link=link)

        except KeyError:
            print sys.exc_info()[0]
            return render_template("error.html", msg="Bad Request!")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/gun_control/label", methods=['POST', 'GET'])
def gun_label():
    if request.method == "POST":
        try:
            survey = mongo.get_survey("Gun Control")
            questions = survey["questions"] if "questions" in survey else []
            collection_batch_name = "gunbatch" #The name of a mongodb collection of documents of batchs
            collection_tweet_name = "guncontrol" #The name of a mongodb collection of documents of tweets
            if 'username' in session:
                username = mongo.get_username(session['username'])
            else:
                return render_template("label.html")

            if request.form["submit"] == "This is spam":
                #If it is a SPAM
                survey = [{"SPAM": True}]
                batch = request.form["batch"]
                tweet_nr = request.form["tweet_nr"]
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, collection_tweet_name)
                if not result:
                    return render_template("error.html", msg="Internal Error")
                tweet_id = request.form["tweetid"]
                mongo.update_label(tweet_id, survey, batch, tweet_nr, collection_tweet_name, collection_batch_name, username)
                if int(tweet_nr) == tweets_per_batch:
                    return render_template("cong.html")
                else:
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr, questions=questions)

            elif escape(request.form["submit"]) == "next":
                #Continue to label next tweet and save the label information

                batch = request.form["batch"]
                tweet_nr = request.form["tweet_nr"]
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, collection_tweet_name)
                if not result:
                    return render_template("error.html", msg="Internal Error")
                tweet_id = request.form["tweetid"]
                survey = []
                prev = -1
                for q in questions:
                    tmp = {"questions": q["text"], "answer": []}
                    answer = request.form.getlist(str(q["_id"]))
                    if answer == []:
                        if "followup" in q and q["followup"] == True:
                            if prev != -1:
                                prev_answer = request.form.getlist(str(prev))[0]
                                if prev_answer == "Yes":
                                    return render_template("error.html", msg="You have to answer question " + str(q["_id"]))
                        else:
                            return render_template("error.html", msg="You haven't answer question " + str(q["_id"]))
                    for a in answer:
                        tmp["answer"].append(a)
                    survey.append(tmp)
                    prev = q["_id"]
                mongo.update_label(tweet_id, survey, batch, tweet_nr, collection_tweet_name, collection_batch_name, username)
                if int(tweet_nr) == tweets_per_batch:
                    return render_template("cong.html")
                else:
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr, questions=questions)
        except KeyError:
            print sys.exc_info()[0]
            return render_template("error.html", msg="Bad Request!")

    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/survey")
def survey():
    #The main page of survey
    lst = ["joshua.tucker@nyu.edu", "bonneau@nyu.edu", "jonathan.nagler@nyu.edu", "chaipeihong@gmail.com"]
    if 'username' in session and session['username'] in lst:
        result = mongo.exist_survey()
        return render_template("survey.html", result=result)
    else:
        return render_template("error.html", msg="You are not authorized to view the following page")


@app.route("/process_survey", methods=["POST", "GET"])
def proces_survey():
    #All the request of survey
    if request.method == "POST":
        try:
            if request.form["submit"] == "Create":
                if mongo.new_survey(request.form["survey"]):
                    return redirect(url_for('survey'))
                else:
                    return render_template("error.html", msg="Bad Request! Survey name already exists")
            elif request.form["submit"] == "Edit":
                survey = mongo.get_survey(request.form["survey_name"])
                description = survey["description"] if "description" in survey else ""
                survey_name = survey["survey_name"]
                questions = survey["questions"] if "questions" in survey else []
                survey_log = survey_name.split(" ")[0]+"_log"
                log = mongo.get_survey_log(survey_log)
                return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
            elif request.form["submit"] == "Delete":
                mongo.drop_survey(request.form["survey_name"])
                return redirect(url_for('survey'))
            elif request.form["submit"] == "Lock":
                mongo.lock_survey(request.form["survey_name"], True)
                return redirect(url_for('survey'))
            elif request.form["submit"] == "Unlock":
                print "here"
                mongo.lock_survey(request.form["survey_name"], False)
                return redirect(url_for('survey'))
        except KeyError:
            return render_template("error.html", msg="Bad Request! Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/edit_survey/description", methods=["POST", "GET"])
def edit_survey_description():
    #All the request of editing survey is processed here
    if request.method == "POST":
        try:
            survey_name = request.form["survey_name"]
            survey = mongo.get_survey(survey_name)
            questions = survey["questions"] if "questions" in survey else []
            description = survey["description"] if "description" in survey else ""
            survey_log = survey_name.split(" ")[0]+"_log"
            username = mongo.get_username(session['username'])
            #Create New description for the survey
            if request.form["submit"] == "Update Description":
                description = request.form["description"]
                log = mongo.get_survey_log(survey_log)
                mongo.update_description(survey_name, description)
                mongo.insert_survey_log(survey_log, username, "Update the description of the survey")
                return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request!Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/edit_survey", methods=["POST", "GET"])
def edit_survey():
    #All the request of editing survey is processed here
    if request.method == "POST":
        try:
            survey_name = request.form["survey_name"]
            survey = mongo.get_survey(survey_name)
            questions = survey["questions"] if "questions" in survey else []
            description = survey["description"] if "description" in survey else ""
            survey_log = survey_name.split(" ")[0]+"_log"
            username = mongo.get_username(session['username'])
            #Create New question
            if "new" in request.form and request.form["new"]:
                question_nr = len(survey["questions"]) + 1 if "questions" in survey else 1
                mongo.insert_survey_log(survey_log, username, "Created a new question")
                return render_template("editsurvey.html", survey_name=survey_name, question_nr=question_nr)
            #Insert a new question
            elif "insert" in request.form and request.form["insert"]:
                question_nr = int(request.form["insert"]) + 1
                mongo.insert_survey_log(survey_log, username, "Insert a new question")
                return render_template("editsurvey.html", survey_name=survey_name, question_nr=question_nr, flag="insert")
            #Edit an existing question
            elif "edit" in request.form and request.form["edit"]:
                question_nr = request.form["edit"]
                question = survey["questions"][int(question_nr)-1]
                answers = ""
                for a in question["answers"]:
                    answers += a["text"] + "\n"
                mongo.insert_survey_log(survey_log, username, "Edited question "+question_nr)
                return render_template("editsurvey.html", survey_name=survey_name, question_nr=question_nr, question=question, answers=answers)
            #Delete an exisitng question
            elif "delete" in request.form and request.form["delete"]:
                question_nr = request.form["delete"]
                mongo.delete_survey(survey_name, question_nr)
                mongo.insert_survey_log(survey_log, username, "Deleted question "+question_nr)
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                questions = survey["questions"] if "questions" in survey else []
                return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
            #Move up an existing question
            elif "up" in request.form and request.form["up"]:
                question_nr = request.form["up"]
                mongo.move_survey(survey_name, question_nr, "up")
                mongo.insert_survey_log(survey_log, username, "Changed the order of the questions")
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                questions = survey["questions"]
                return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
            #Move down an existing question
            elif "down" in request.form and request.form["down"]:
                question_nr = request.form["down"]
                mongo.move_survey(survey_name, question_nr, "down")
                mongo.insert_survey_log(survey_log, username, "Changed the order of the questions")
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                questions = survey["questions"]
                return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to select a question! Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/build_survey", methods=["POST", "GET"])
def build_survey():
    #Edit or create the actual question and answer
    if request.method == "POST":
        try:
            question_text = request.form["question"].strip()
            answer_text = request.form["answers"].strip()
            option = request.form["option"]
            answers = answer_text.split("\n")
            survey_name = request.form["survey_name"]
            question_nr = request.form["question_nr"]
            followup = False
            if "followup" in request.form and request.form["followup"] == "true":
                followup = True
            lst = []
            for a in answers:
                if a:
                    lst.append({"answer_nr": answers.index(a), "text": a.strip("\r")})
            question = {"_id": int(question_nr), "option": option, "followup" : followup, "text": question_text, "answers": lst}
            if request.form["submit"] == "Finish":
                mongo.update_survey(survey_name, question)
            elif request.form["submit"] == "Insert":
                mongo.insert_survey_question(survey_name, question_nr, question)
            survey = mongo.get_survey(survey_name)
            questions = survey["questions"] if "questions" in survey else []
            description = survey["description"] if "description" in survey else ""
            survey_log = survey_name.split(" ")[0]+"_log"
            log = mongo.get_survey_log(survey_log)
            return render_template("surveypage.html", survey_name=survey_name, questions=questions, description=description, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to fill in the question and answer")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


if __name__ == "__main__":
    """ Connect to MongoDB """
    mongo = MongoDBCoordinator("128.122.79.158", "LabelTweets", port=10000)
    app.secret_key = '\xa0\x1e\x95t\xcf\x7f\xe3J\xdf\x96D{98\x91iR\xb6\xfa\xb6g\xfc\x0fB'
    app.debug = True
    app.run(host='localhost', port=8080)
