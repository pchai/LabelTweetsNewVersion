#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Peihong Chai on 2013-01-28.
# Copyright (c) , under the Simplified BSD License.
# For more information on FreeBSD see: http://www.opensource.org/licenses/bsd-license.php
# All rights reserved.
"""
import simplejson as json

from flask import Flask
from flask import render_template
from flask import session, redirect, url_for, escape, request

from MongoCoordinator import MongoDBCoordinator


app = Flask(__name__)


def gun_label_helper():
    f = open('gun_survey.json', 'r')
    data = json.loads(f.read())
    return data


@app.route("/")
def hello():
    return render_template('hello.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == "POST":
        try:
            if mongo.validate_signup(escape(request.form["emailSignup"])):
                mongo.insert_login(request.form["emailSignup"], request.form["userName"])
                session['username'] = escape(request.form["emailSignup"])
                return render_template("select.html")
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
            if mongo.valid_login(escape(request.form["emailSignin"])):
                session['username'] = escape(request.form["emailSignin"])
                return render_template("select.html")
            else:
                return render_template("error.html", msg="No record exists, go back an signup")
        except KeyError:
            return render_template("error.html", msg="Bad Operation! You have to fill in your email address")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/select", methods=['POST', 'GET'])
def select():
    if request.method == "POST":
        try:
            if request.form["guncontrol"] == "Gun Control":
                return redirect(url_for('gun_mainpage'))
        except KeyError:
            return render_template("error.html", msg="Bad Request! You should select an option")


@app.route("/gun_control/mainpage/", defaults={'page': 1})
@app.route("/gun_control/mainpage/<int:page>")
def gun_mainpage(page):
    if 'username' in session:
        username = mongo.get_username(escape(session['username']))
        result = mongo.get_batchs(skip_nr=page - 1, batch="gunbatch")
        batchs = mongo.get_pull_batch(escape(session['username']), "guncontrol")
        return render_template("main.html", username=username, result=result, page=page, batchs=batchs)
    else:
        return render_template("main.html")


@app.route("/gun_control/pull", methods=['POST', 'GET'])
def gun_pull():
    if request.method == "POST":
        try:
            if 'username' in session:
                email = session['username']
                batch_nr = request.form["batch"]
                mongo.add_batch(batch_nr, "gunbatch", email, "guncontrol")
                return redirect(url_for('gun_mainpage'))
            else:
                return render_template("error.html", msg="You are not logged in")
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to pull a batch before confirming")

    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/survey")
def survey():
    #The main page of survey
    lst=["chaipeihong@gmail.com"]
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
            if request.form["submit"] == "Edit":
                survey = mongo.get_survey(request.form["exist_survey"])
                survey_name = survey["survey_name"]
                if "questions" not in survey:
                    questions = []
                else:
                    questions = survey["questions"]
                return render_template("surveypage.html", survey_name=survey_name, questions=questions)

        except KeyError:
            return render_template("error.html", msg="Bad Request! Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/edit_survey", methods=["POST", "GET"])
def edit_survey():
    #All the request of editing survey is processed here
    if request.method == "POST":
        try:
            survey_name = request.form["survey_name"]
            question_nr = request.form["question_nr"]
            survey = mongo.get_survey(survey_name)
            if "questions" not in survey:
                questions = []
            else:
                questions = survey["questions"]
            survey_log = survey_name+"_log"
            #Create New question
            if request.form["submit"] == "New Question":
                if "questions" not in survey:
                    question_nr = 1
                else:
                    question_nr = len(survey["questions"]) + 1
                return render_template("editsurvey.html", survey_name=survey_name, question_nr=question_nr)
            #Edit an existing question
            if request.form["submit"] == "Edit Question":
                question = survey["questions"][int(question_nr)-1]
                answers = ""
                for a in question["answers"]:
                    answers += a["text"] + "\n"
                return render_template("editsurvey.html", survey_name=survey_name, question_nr=question_nr, question=question, answers=answers)
            #Delete an exisitng question
            if request.form["submit"] == "Delete Question":
                mongo.delete_survey(survey_name, question_nr)
                return render_template("surveypage.html", survey_name=survey_name, questions=questions)
            #Move up an existing question
            if request.form["submit"] == "Move Up":
                mongo.move_survey(survey_name, question_nr, "up")
                return render_template("surveypage.html", survey_name=survey_name, questions=questions)
            #Move down an existing question
            if request.form["submit"] == "Move Down":
                mongo.move_survey(survey_name, question_nr, "down")
                return render_template("surveypage.html", survey_name=survey_name, questions=questions)
        except KeyError:
            return render_template("error.html", msg="Bad Request! Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/build_survey", methods=["POST", "GET"])
def build_survey():
    #Edit or create the actual question and answer
    if request.method == "POST":
        try:
            if request.form["submit"] == "Finish":
                question_text = request.form["question"].strip()
                print question_text
                answer_text = request.form["answers"].strip()
                option = request.form["option"]
                answers = answer_text.split("\n")
                survey_name = request.form["survey_name"]
                question_nr = request.form["question_nr"]
                lst = []
                for a in answers:
                    if a != "":
                        lst.append({"answer_nr": answers.index(a), "text": a.strip("\r")})
                question = {"_id": int(question_nr), "option": option, "text": question_text, "answers": lst}
                mongo.update_survey(survey_name, question)
                survey = mongo.get_survey(survey_name)
                if "questions" not in survey:
                    questions = []
                else:
                    questions = survey["questions"]
                return render_template("surveypage.html", survey_name=survey_name, questions=questions)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to fill in the question and answer")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/gun_control/label", methods=['POST', 'GET'])
def gun_label():
    if request.method == "POST":
        if escape(request.form["submit"]) == "Go to Label":
            try:
                if request.form["pull_batch"]:
                    if 'username' in session:
                        username = mongo.get_username(escape(session['username']))
                    else:
                        return render_template("label.html")
                    batch = request.form["pull_batch"]
                    tweet_nr = mongo.get_labelled(batch, "gunbatch", username)
                    if tweet_nr == 100:
                        return render_template("error.html", msg="Finished Batch! This batch is already been labelled")
                    result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)
            except KeyError:
                return render_template("error.html", msg="Bad Request! You have to select a batch if you want to label")
        elif escape(request.form["submit"]) == "Not English":
            if 'username' in session:
                username = mongo.get_username(escape(session['username']))
            else:
                return render_template("label.html")
            option = {"not_english": True}
            batch = request.form["batch"]
            tweet_nr = request.form["tweet_nr"]
            cong = False
            if int(tweet_nr) == 100:
                cong = True
            else:
                cong = False
            result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
            tweet_id = request.form["tweetid"]
            mongo.update_label(tweet_id, option, batch, tweet_nr, "guncontrol", "gunbatch", username)
            if cong:
                return render_template("cong.html")
            else:
                return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)

        elif escape(request.form["submit"]) == "next":
            try:
                if 'username' in session:
                    username = mongo.get_username(escape(session['username']))

                else:
                    return render_template("label.html")
                batch = request.form["batch"]
                tweet_nr = request.form["tweet_nr"]
                cong = False
                if int(tweet_nr) == 100:
                    cong = True
                else:
                    cong = False
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
                tweet_id = request.form["tweetid"]
                option = gun_label_helper()
                #Update topic section of the survey
                #Update sentiment section of the survey
                topic = option["topic"]
                sentiment = option["sentiment"]
                if "newtown" in request.form:
                    topic["newtown"] = True
                    sentiment["newtown"][request.form["newtown"]] = True
                if "guncontrol" in request.form:
                    topic["guncontrol"] = True
                    sentiment["guncontrol"][request.form["guncontrol"]] = True
                if "nra" in request.form:
                    topic["nra"] = True
                    sentiment["nra"][request.form["nra"]] = True
                if "unsure" in request.form:
                    topic["unsure"] = True

                #Update emotion section of the survey
                emotion = option["emotion"]
                if "emotion" in request.form and request.form["emotion"] == "Yes":
                    if "anger" in request.form and request.form["anger"] == "true":
                        emotion["anger"] = True
                    if "sad" in request.form and request.form["sad"] == "true":
                        emotion["sad"] = True
                    if "sympathy" in request.form and request.form["sympathy"] == "true":
                        emotion["sympathy"] = True
                    if "groupidentity" in request.form and request.form["groupidentity"] == "true":
                        emotion["groupidentity"] = True

                #Update information section of the survey
                information = option["information"]
                if "information" in request.form and request.form["information"] == "Yes":
                    if "fact" in request.form and request.form["fact"] == "true":
                        information["fact"] = True
                    if "existing" in request.form and request.form["existing"] == "true":
                        information["existing"] = True
                    if "change" in request.form and request.form["change"] == "true":
                        information["change"] = True
                    if "event" in request.form and request.form["event"] == "true":
                        information["event"] = True

                #Update goal section of the survey
                goal = option["goal"]
                if "goal" in request.form and request.form["goal"] == "Yes":
                    if "petition" in request.form and request.form["petition"] == "true":
                        goal["petition"] = True
                    if "protest" in request.form and request.form["protest"] == "true":
                        goal["protest"] = True
                    if "denotion" in request.form and request.form["denotion"] == "true":
                        goal["denotion"] = True
                    if "voting" in request.form and request.form["voting"] == "true":
                        goal["voting"] = True

                #Update Author section of the survey
                author = option["author"]
                author[request.form["org"]] = True

                #Update sentiment section of the survey
                link = option["link"]
                link[request.form["link"]] = True

                mongo.update_label(tweet_id, option, batch, tweet_nr, "guncontrol", "gunbatch", username)
                if cong:
                    return render_template("cong.html")
                else:
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)
            except KeyError:
                return render_template("error.html", msg="Bad Request! You have to answer all the questions")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


if __name__ == "__main__":
    """ Connect to MongoDB """
    mongo = MongoDBCoordinator("128.122.79.158", "LabelTweets", port=10000)
    app.secret_key = '\xa0\x1e\x95t\xcf\x7f\xe3J\xdf\x96D{98\x91iR\xb6\xfa\xb6g\xfc\x0fB'
    app.debug = True
    app.run(host='localhost', port=8080)
