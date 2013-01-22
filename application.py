from flask import Flask
from flask import render_template

from flask import session, redirect, url_for, escape, request

from MongoCoordinator import MongoDBCoordinator


app = Flask(__name__)


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
                return redirect(url_for('mainpage'))
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
                    return redirect(url_for('mainpage'))
        except KeyError:
            return "Bad Operation! You have to fill in your email address"
    else:
        return "Bad Request! Shouldn't come here"


@app.route("/mainpage/", defaults={'page': 1})
@app.route("/mainpage/<int:page>")
def mainpage(page):
    if 'username' in session:
        username = mongo.get_username(escape(session['username']))
        result = mongo.get_batchs(skip_nr=page - 1, batch="gunbatch")
        batchs = mongo.get_pull_batch(escape(session['username']), "guncontrol")
        return render_template("main.html", username=username, result=result, page=page, batchs=batchs)
    else:
        return render_template("main.html")


@app.route("/pull", methods=['POST', 'GET'])
def pull():
    if request.method == "POST":
        try:
            if request.form["batch"]:
                if 'username' in session:
                    email = escape(session['username'])
                    mongo.add_batch(request.form["batch"], "gunbatch", email, "guncontrol")
                    return redirect(url_for('mainpage'))
                else:
                    return 'You are not logged in'
        except KeyError:
            return 'Bad Request! You have to select a batch to pull, go back and select!'
    else:
        return "Bad Request! Shouldn't come here"


@app.route("/label", methods=['POST', 'GET'])
def label():
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
                    option = request.form["option"]
                    mongo.update_label(tweet_id, option, batch, tweet_nr, "guncontrol", "gunbatch")
                    return render_template("label.html", batch=batch, username=username, result=result, tweet_nr=tweet_nr)
            except KeyError:
                return "Bad request! You have to select an option to label"
    else:
        return "Bad Request! Shouldn't come here"


if __name__ == "__main__":
    """ Connect to MongoDB """
    mongo = MongoDBCoordinator("localhost", "LabelTweets", port=10000)
    app.secret_key = '\xa0\x1e\x95t\xcf\x7f\xe3J\xdf\x96D{98\x91iR\xb6\xfa\xb6g\xfc\x0fB'
    app.debug = True
    app.jinja_env.globals['mainpage'] = mainpage
    app.run(host='128.122.79.158', port=8080)
