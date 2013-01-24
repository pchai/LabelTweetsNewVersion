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


@app.route("/hello")
def hello():
    return render_template('hello.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == "POST":
        try:
            if mongo.valid_login(request.form["emailSignup"]) == "NoRecord":
                mongo.insert_login(request.form["emailSignup"], request.form["userName"])
                session['username'] = mongo.valid_login(request.form["emailSignup"])
                return render_template("select.html")
            else:
                return "You have got a email address registered, go back and login using your email address"
        except KeyError:
            print "enter here"
            return "Bad Operation! You have to fill in your email address and username"
    else:
        return "Bad Request! Shouldn't come here"


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        try:
            if request.form["emailSignin"]:
                if mongo.valid_login(request.form["emailSignin"]) == "NoRecord":
                    return 'No record exists, go back and sign up'
                else:
                    session['username'] = mongo.valid_login(request.form["emailSignin"])
                    return render_template("select.html")
        except KeyError:
            return "Bad Operation! You have to fill in your email address"
    else:
        return "Bad Request! Shouldn't come here"


@app.route("/select", methods=['POST', 'GET'])
def select():
    if request.method == "POST":
        try:
            if request.form["guncontrol"] == "Gun Control":
                return redirect(url_for('gun_mainpage'))
        except KeyError:
            return "Bad Operation! You have to select an option"


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
            if request.form["batch"]:
                if 'username' in session:
                    email = escape(session['username'])
                    mongo.add_batch(request.form["batch"], "gunbatch", email, "guncontrol")
                    return redirect(url_for('gun_mainpage'))
                else:
                    return 'You are not logged in'
        except KeyError:
            return 'Bad Request! You have to select a batch to pull, go back and select!'
    else:
        return "Bad Request! Shouldn't come here"


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
                    tweet_nr = mongo.get_labelled(batch, "gunbatch")
                    result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)
            except KeyError:
                return "Bad request! You have to select a f if you want to label"
        elif escape(request.form["submit"]) == "Not English":
            if 'username' in session:
                username = mongo.get_username(escape(session['username']))
            else:
                return render_template("label.html")
            batch = request.form["batch"]
            tweet_nr = request.form["tweet_nr"]
            if int(tweet_nr) == 100:
                return render_template("cong.html")
            else:
                result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
                tweet_id = request.form["tweetid"]
            option = {"not_english": True}
            mongo.update_label(tweet_id, option, batch, tweet_nr, "guncontrol", "gunbatch")
            return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)

        elif escape(request.form["submit"]) == "next":
            try:
                if 'username' in session:
                    username = mongo.get_username(escape(session['username']))
                else:
                    return render_template("label.html")
                batch = request.form["batch"]
                tweet_nr = request.form["tweet_nr"]
                if int(tweet_nr) == 100:
                    return render_template("cong.html")
                else:
                    result = mongo.get_tweet(int(batch), int(tweet_nr) + 1, "guncontrol")
                    tweet_id = request.form["tweetid"]
                    option = gun_label_helper()

                    #Update topic section of the survey
                    topic = option["topic"]
                    if "newtown" in request.form and request.form["newtown"] == "true":
                        topic["newtown"] = True
                    if "guncontrol" in request.form and request.form["guncontrol"] == "true":
                        topic["guncontrol"] = True
                    if "nra" in request.form and request.form["nra"] == "true":
                        topic["nra"] = True
                    if "unsure" in request.form and request.form["unsure"] == "true":
                        topic["unsure"] = True

                    #Update sentiment section of the survey
                    sentiment = option["sentiment"]
                    sentiment[request.form["sentiment"]] = True

                    #Update emotion section of the survey
                    emotion = option["emotion"]
                    if "anger" in request.form and request.form["anger"] == "true":
                        emotion["anger"] = True
                        print "anger is true"
                    if "sad" in request.form and request.form["sad"] == "true":
                        emotion["sad"] = True
                    if "sympathy" in request.form and request.form["sympathy"] == "true":
                        emotion["sympathy"] = True
                    if "groupidentity" in request.form and request.form["groupidentity"] == "true":
                        emotion["groupidentity"] = True

                    #Update organization section of the survey
                    organization = option["organization"]
                    organization[request.form["org"]] = True

                    #Update information section of the survey
                    information = option["information"]
                    if "past_regulation" in request.form and request.form["past_regulation"] == "true":
                        information["past_regulation"] = True
                    if "call_to_action" in request.form and request.form["call_to_action"] == "true":
                        information["call_to_action"] = True

                    #Update sentiment section of the survey
                    link = option["link"]
                    link[request.form["information"]] = True

                    mongo.update_label(tweet_id, option, batch, tweet_nr, "guncontrol", "gunbatch")
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)
            except KeyError:
                return "Bad request! You have to select an option for each question to label. Go Back!"
    else:
        return "Bad Request! Shouldn't come here"


if __name__ == "__main__":
    """ Connect to MongoDB """
    mongo = MongoDBCoordinator("128.122.79.158", "LabelTweets", port=10000)
    app.secret_key = '\xa0\x1e\x95t\xcf\x7f\xe3J\xdf\x96D{98\x91iR\xb6\xfa\xb6g\xfc\x0fB'
    app.debug = True
    app.run(host='localhost', port=8080)
