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
                return render_template("error.html", msg="You have got a email address registered, go back and login using your email address")
        except KeyError:
                return render_template("error.html", msg="Bad Operation! You have to fill in your email address and username")
    else:
        return render_template("error.html", msg="Bad Request! Shouldn't come here")


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        try:
            if mongo.valid_login(request.form["emailSignin"]) == "NoRecord":
                return render_template("error.html", msg="No record exists, go back an signup")
            else:
                session['username'] = mongo.valid_login(request.form["emailSignin"])
                return render_template("select.html")
        except KeyError:
            #return "Bad Request"
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
                email = escape(session['username'])
                batch_nr = escape(request.form["batch"])
                mongo.add_batch(batch_nr, "gunbatch", email, "guncontrol")
                return redirect(url_for('gun_mainpage'))
            else:
                return render_template("error.html", msg="You are not logged in")
        except KeyError:
            return render_template("error.html", msg="Bad Request! You have to pull a batch before confirming")

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
