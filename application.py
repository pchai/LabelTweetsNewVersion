#!/usr/bin/env python
# encoding: utf-8
"""
application.py

Created by Peihong Chai on 2013-01-28.
# Copyright (c) , under the Simplified BSD License.
# For more information on FreeBSD see: http://www.opensource.org/licenses/bsd-license.php
# All rights reserved.
"""
import sys
import StringIO
import re
import pytz
import datetime
from flask import Flask
from flask import render_template
from flask import session, redirect, url_for, escape, request
from flask import Response
from MongoCoordinator import MongoDBCoordinator
from werkzeug.datastructures import Headers

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
            if 'username' in session:
                survey = request.form["survey"]
                if session['username'] in mongo.get_survey(survey)["admin"]:
                    return redirect(url_for('admin_page', survey=survey, page=1))
                else:
                    return redirect(url_for('main_page', survey=survey))
        except KeyError:
            return render_template("error.html", msg="Bad Request! You should select an option")
    else:
        if 'username' in session:
            result = mongo.exist_survey()
            return render_template("select.html", result=result)
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/redirect/<survey>")
def redirecting(survey):
    if 'username' in session:
        if session['username'] in mongo.get_survey(survey)["admin"]:
            return redirect(url_for('admin_page', survey=survey, page=1))
        else:
            return redirect(url_for('main_page', survey=survey, page=1))

@app.route("/admin/<survey>/<int:page>")
def admin_page(survey, page):
    '''Main Coding page for internal'''
    survey_data = mongo.get_survey(survey)
    if 'username' in session and session['username'] in survey_data["admin"]:
        username = mongo.get_username(session['username'])
        result = mongo.get_batchs(skip_nr=page - 1, batch=survey_data["batch"], survey=survey)
        if not result:
            return render_template("error.html", msg="Internal Error")
        batchs = mongo.get_pull_batch(session['username'], survey_data["tweets"])
        survey = mongo.get_survey(survey)
        description = survey["description"] if "description" in survey else ""
        lock = survey["lock"] if "lock" in survey else ""
        return render_template("admin.html", username=username, survey_name=survey_data["survey_name"],
            result=result, page=page, batchs=batchs, description=description, lock=lock)
    else:
        return render_template("admin.html")

@app.route("/main/<survey>/")
def main_page(survey):
    '''Main Coding page for Coder'''
    if 'username' in session:
        survey_data = mongo.get_survey(survey)
        username = mongo.get_username(session['username'])
        result = mongo.get_batchs(skip_nr=0, batch=survey_data["batch"], survey=survey)
        batchs = mongo.get_pull_batch(session['username'], survey_data["tweets"])
        description = survey_data["description"] if "description" in survey_data else ""
        lock = survey_data["lock"] if "lock" in survey_data else ""
        return render_template("main.html", username=username, survey_name=survey_data["survey_name"],
            result=result, batchs=batchs, description=description, lock=lock)
    else:
        return render_template("main.html")

@app.route("/<survey>/pull", methods=['POST', 'GET'])
def pull(survey):
    if request.method == "POST":
        try:
            survey_data = mongo.get_survey(survey)

            if 'username' in session:
                email = session['username']
                if "pull" in request.form and request.form["pull"]:
                    batch_nr = request.form["pull"]
                    mongo.add_batch(batch_nr, survey_data["batch"], email, survey_data["tweets"])
                    return redirect(url_for('admin_page', survey=survey, page=1))
            else:
                return render_template("error.html", msg="You are not logged in")
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to pull a batch before confirming")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/<survey>/startconding", methods=['POST', 'GET'])
def start_coding(survey):
    if request.method == "POST":
        try:
            survey_data = mongo.get_survey(survey)
            collection_batch_name = survey_data["batch"] #The name of a mongodb collection of documents of batchs
            collection_tweet_name = survey_data["tweets"] #The name of a mongodb collection of documents of tweets
            if 'username' in session:
                username = mongo.get_username(session['username'])
            else:
                return render_template("label.html")
            if "code" in request.form and request.form["code"] == "true":
                #Enter where you left last time
                batch = request.form["pull_batch"]
                tweet_nr = mongo.get_labelled(batch, collection_batch_name, username)
                if tweet_nr == tweets_per_batch:
                    return render_template("error.html", msg="Finished Batch! All the tweets in this batch has been labelled")
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, collection_tweet_name)
                if not result:
                    return render_template("error.html", msg="Internal Error")
                return render_template("label.html", batch=batch, username=escape(username), result=result, tweet_nr=tweet_nr, survey=survey_data)
            elif "back" in request.form and request.form["back"] == "true":
                batch = request.form["pull_batch"]
                tweet_nr = mongo.get_labelled(batch, collection_batch_name, username)
                if tweet_nr == 0:
                    mongo.put_back_batch(int(batch), collection_batch_name, session['username'], collection_tweet_name)
                    return redirect(url_for('redirecting', survey=survey))
                else:
                    return render_template("error.html", msg="Couldn't put it back since you have already labelled this batch")
            elif "pull" in request.form and request.form["pull"] == "true":
                batch_nr = mongo.get_next_batch(collection_batch_name, survey, username)
                mongo.add_batch(batch_nr, collection_batch_name, session['username'], collection_tweet_name)
                return redirect(url_for('redirecting', survey=survey))

        except KeyError:
            return render_template("error.html", msg="Bad Request!")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/<survey>/label", methods=['POST', 'GET'])
def label(survey):
    if request.method == "POST":
        try:
            survey_data = mongo.get_survey(survey)
            collection_batch_name = survey_data["batch"] #The name of a mongodb collection of documents of batchs
            collection_tweet_name = survey_data["tweets"] #The name of a mongodb collection of documents of tweets
            if 'username' in session:
                username = mongo.get_username(session['username'])
            else:
                return render_template("label.html")

            if request.form["submit"] == "This is spam":
                #If it is a SPAM
                survey = {"SPAM": True}
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
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr, survey=survey_data)

            elif request.form["submit"] == "next":
                #Continue to label next tweet and save the label information
                batch = request.form["batch"]
                tweet_nr = request.form["tweet_nr"]
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, collection_tweet_name)
                if not result:
                    return render_template("error.html", msg="Internal Error")
                tweet_id = request.form["tweetid"]
                survey = {}
                survey["tweet_id"] = tweet_nr
                survey["coder_name"] = username
                survey["code_time"] = str(datetime.datetime.now(pytz.timezone('US/Eastern')))
                for q in survey_data["questions"]:
                    question_nr = q["_id"]
                    if "matrix" in q and q["matrix"] == True:
                        checked_answer = []
                        for r in q["row_choices"]:
                            lst = request.form.getlist(r["text"])
                            for e in lst:
                                checked_answer.append(e.split("|"))
                        for r in q["row_choices"]:
                            for c in q["column_choices"]:
                                if [r,c] in checked_answer:
                                    survey["Q_"+ str(question_nr) + "_" + str(r["answer_nr"] + 1) + "_" +str(c["answer_nr"] + 1)] = 1
                                else:
                                    survey["Q_"+ str(question_nr) + "_" + str(r["answer_nr"] + 1) + "_" + str(c["answer_nr"] + 1)] = 0      
                    else:
                        answers = q["answers"]
                        checked_answer = request.form.getlist(str(q["_id"]))
                        if checked_answer == [] and q["option"] != "any":       
                            return render_template("error.html", msg="You have to answer question " + str(q["_id"]))
                        for a in answers:
                            if a["text"] in checked_answer:
                                survey["Q_" + str(question_nr) + "_" + str(a["answer_nr"] + 1)] = 1
                            else:
                                survey["Q_" + str(question_nr) + "_" + str(a["answer_nr"] + 1)] = 0
                #print survey
                mongo.update_label(tweet_id, survey, batch, tweet_nr, collection_tweet_name, collection_batch_name, username)
                if int(tweet_nr) == tweets_per_batch:
                    return render_template("cong.html")
                else:
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr, survey=survey_data)
        except KeyError:
            print sys.exc_info()[0]
            return render_template("error.html", msg="Bad Request!")

    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/survey")
def survey():
    #The main page of survey
    if session['username'] in mongo.get_admins():
        result = mongo.exist_survey()
        return render_template("survey.html", result=result)
    else:
        return render_template("error.html", msg="You are not authorized to view the following page")

@app.route("/process_survey", methods=["POST", "GET"])
def proces_survey():
    #All the request of survey
    if request.method == "POST":
        try:
            if "edit" in request.form and request.form["edit"]:
                survey_name = request.form["edit"]
                survey = mongo.get_survey(survey_name)
                if session["username"] in survey["admin"]:
                    survey_log = survey_name.split(" ")[0]+"_log"
                    log = mongo.get_survey_log(survey_log)
                    result = mongo.exist_survey()
                    return render_template("surveypage.html", survey=survey, result=result, log=log)
                else:
                    return render_template("error.html", msg="You're not authorized to edit this survey")
            elif "lock" in request.form and request.form["lock"]:
                survey_name = request.form["lock"]
                survey = mongo.get_survey(survey_name)
                if session["username"] in survey["admin"]:
                    mongo.lock_survey(request.form["lock"], True)
                    return redirect(url_for('survey'))
                else:
                    return render_template("error.html", msg="You're not authorized to lock this survey")
            elif "unlock" in request.form and request.form["unlock"]:
                survey_name = request.form["unlock"]
                survey = mongo.get_survey(survey_name)
                if session["username"] in survey["admin"]:
                    mongo.lock_survey(request.form["unlock"], False)
                    return redirect(url_for('survey'))
                else:
                    return render_template("error.html", msg="You're not authorized to unlock this survey")
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
            survey_log = survey_name.split(" ")[0]+"_log"
            username = mongo.get_username(session['username'])
            #Create New description for the survey
            if request.form["submit"] == "Update Description":
                description = request.form["description"]
                log = mongo.get_survey_log(survey_log)
                mongo.update_description(survey_name, description)
                mongo.insert_survey_log(survey_log, username, "Update the description of the survey")
                result = mongo.exist_survey()
                survey = mongo.get_survey(survey_name)
                return render_template("surveypage.html", survey=survey, result=result, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request!Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/edit_survey/intercode", methods=["POST", "GET"])
def edit_survey_intercode():
    if request.method == "POST":
        try:
            survey_name = request.form["survey_name"]
            survey = mongo.get_survey(survey_name)
            survey_log = survey_name.split(" ")[0]+"_log"
            username = mongo.get_username(session['username'])
            #Create New description for the survey
            if "apply" in request.form and request.form["apply"]:
                if "applyintercode" in request.form and request.form["applyintercode"] == "true":
                    intercode = True
                else:
                    intercode = False
                if "fold" in request.form and request.form["fold"]:
                    fold = request.form["fold"]
                else:
                    fold = 1
                mongo.update_intercode(survey_name, intercode, fold)
                log = mongo.get_survey_log(survey_log)
                mongo.insert_survey_log(survey_log, username, "Change the intercode reliability")
                result = mongo.exist_survey()
                survey = mongo.get_survey(survey_name)
                return render_template("surveypage.html", survey=survey, result=result, log=log)
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
            survey_log = survey_name.split(" ")[0]+"_log"
            username = mongo.get_username(session['username'])
            #Create New question
            if "new" in request.form and request.form["new"]:
                question_nr = len(survey["questions"]) + 1 if "questions" in survey else 1
                mongo.insert_survey_log(survey_log, username, "Created a new question")
                return render_template("editQuestion.html", survey_name=survey_name, question_nr=question_nr)
            #Insert a new question
            elif "insert" in request.form and request.form["insert"]:
                question_nr = int(request.form["insert"]) + 1
                mongo.insert_survey_log(survey_log, username, "Insert a new question")
                return render_template("editQuestion.html", survey_name=survey_name, question_nr=question_nr, flag="insert")
            #Edit an existing question
            elif "edit" in request.form and request.form["edit"]:
                question_nr = request.form["edit"]
                question = survey["questions"][int(question_nr)-1]
                if "matrix" in question and question["matrix"] == True:
                    row_choices = ""
                    for r in question["row_choices"]:
                        row_choices += r["text"] + "\n"
                    column_choices = ""
                    for c in question["column_choices"]:
                        column_choices += c["text"] + "\n"
                    mongo.insert_survey_log(survey_log, username, "Edited question " + question_nr)
                    return render_template("editMatrixQuestion.html", survey_name=survey_name, question_nr=question_nr, 
                            question=question, row_choices=row_choices, column_choices=column_choices)
                else:
                    answers = ""
                    for a in question["answers"]:
                        answers += a["text"] + "\n"
                    mongo.insert_survey_log(survey_log, username, "Edited question " + question_nr)
                    return render_template("editQuestion.html", survey_name=survey_name, question_nr=question_nr, question=question, answers=answers)
            #Delete an exisitng question
            elif "delete" in request.form and request.form["delete"]:
                question_nr = request.form["delete"]
                mongo.delete_survey(survey_name, question_nr)
                mongo.insert_survey_log(survey_log, username, "Deleted question "+question_nr)
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                result = mongo.exist_survey()
                survey = mongo.get_survey(survey_name)
                return render_template("surveypage.html", survey=survey, result=result, log=log)
            #Move up an existing question
            elif "up" in request.form and request.form["up"]:
                question_nr = request.form["up"]
                mongo.move_survey(survey_name, question_nr, "up")
                mongo.insert_survey_log(survey_log, username, "Changed the order of the questions")
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                result = mongo.exist_survey()
                survey = mongo.get_survey(survey_name)
                return render_template("surveypage.html", survey=survey, result=result, log=log)
            #Move down an existing question
            elif "down" in request.form and request.form["down"]:
                question_nr = request.form["down"]
                mongo.move_survey(survey_name, question_nr, "down")
                mongo.insert_survey_log(survey_log, username, "Changed the order of the questions")
                log = mongo.get_survey_log(survey_log)
                survey = mongo.get_survey(survey_name)
                result = mongo.exist_survey()
                survey = mongo.get_survey(survey_name)
                return render_template("surveypage.html", survey=survey, result=result, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to select a question! Go Back")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/matrix_question", methods=["POST", "GET"])
def matrix_question():
    if request.method == "POST":
        try:
            survey_name = request.form["survey_name"]
            question_nr = request.form["question_nr"]
            return render_template("editMatrixQuestion.html", survey_name=survey_name, question_nr=question_nr)
        except KeyError:
            return render_template("error.html", msg="Bad Request!")
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
            survey_log = survey_name.split(" ")[0]+"_log"
            log = mongo.get_survey_log(survey_log)
            result = mongo.exist_survey()
            survey = mongo.get_survey(survey_name)
            return render_template("surveypage.html", survey=survey, result=result, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to fill in the question and answer")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/build_matrix_survey", methods=["POST", "GET"])
def build_matrix_survey():
    #Edit or create the actual matrix question and answer
    if request.method == "POST":
        try:
            question_text = request.form["question"].strip()
            row_choices = request.form["row_choices"].strip().split("\n")
            column_choices = request.form["column_choices"].strip().split("\n")
            rows =[]
            cols = []
            for r in row_choices:
                rows.append({"answer_nr": row_choices.index(r), "text": r.strip("\r")})
            for c in column_choices:
                cols.append({"answer_nr": column_choices.index(c), "text": c.strip("\r")})
            option = request.form["option"]
            survey_name = request.form["survey_name"]
            question_nr = request.form["question_nr"]
            matrix = True
            followup = False
            if "followup" in request.form and request.form["followup"] == "true":
                followup = True
            question = {"_id": int(question_nr), "option": option, "followup" : followup, "text": question_text, 
                "row_choices": rows, "column_choices": cols, "matrix": matrix}
            if request.form["submit"] == "Finish":
                mongo.update_survey(survey_name, question)
            elif request.form["submit"] == "Insert":
                mongo.insert_survey_question(survey_name, question_nr, question)
            survey = mongo.get_survey(survey_name)
            survey_log = survey_name.split(" ")[0]+"_log"
            log = mongo.get_survey_log(survey_log)
            result = mongo.exist_survey()
            survey = mongo.get_survey(survey_name)
            return render_template("surveypage.html", survey=survey, result=result, log=log)
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to fill in the question and answer")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

@app.route("/edit_survey/save_survey", methods=["POST", "GET"])
def save_survey():
    #Edit or create the actual question and answer
    if request.method == "POST":
        try:
            username = mongo.get_username(session['username'])
            if "save" in request.form and request.form["save"] == "true":
                survey_name = request.form["survey_name"]
                survey = mongo.get_survey(survey_name)
                output = StringIO.StringIO()
                response = Response()
                response.status_code = 200
                output.write(survey_name + "\n")
                if "questions" in survey:
                    for q in survey["questions"]:
                        output.write("\n" + str(q["_id"]) + ". " + q["text"] + "\n")
                        for a in q["answers"]:
                            output.write(a["text"] + "\n")
                response.data = output.getvalue()
                response_headers = Headers({
                    'Pragma': "public",  # required,
                    'Expires': '0',
                    'Content-Type': "text/plain",
                    'Content-Disposition': 'attachment; filename= \"%s\";' % (survey_name + ".txt"),
                    'Content-Transfer-Encoding': 'binary',
                    'Content-Length': len(response.data)
                })
                response.headers = response_headers
                return response
            elif "load" in request.form and request.form["load"] == "true":
                if request.form["option"]:
                    load_survey_name = request.form["option"]
                    survey_name = request.form["survey_name"]
                    mongo.load_survey(survey_name, load_survey_name)
                    survey = mongo.get_survey(survey_name)
                    survey_log = survey_name.split(" ")[0]+"_log"
                    log = mongo.get_survey_log(survey_log)
                    result = mongo.exist_survey()
                    mongo.insert_survey_log(survey_log, username, "load a new survey from " + request.form["option"])
                    survey = mongo.get_survey(survey_name)
                    return render_template("surveypage.html", survey=survey, result=result, log=log)
                else:
                    return render_template("error.html", msg="Bad Request! You have to select a survey to load")

        except KeyError:
            return render_template("error.html", msg="Bad Request!")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")

if __name__ == "__main__":
    try:
        """ Connect to MongoDB """
        mongo = MongoDBCoordinator("128.122.79.140", "LabelTweets", port=10000)
        app.secret_key = '\xa0\x1e\x95t\xcf\x7f\xe3J\xdf\x96D{98\x91iR\xb6\xfa\xb6g\xfc\x0fB'
        app.debug = True
        app.run(host='localhost', port=8080)
    except:
        print sys.exc_info()[0]

