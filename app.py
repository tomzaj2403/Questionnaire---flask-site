import sqlite3
import smtplib, ssl

from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from flask_session import Session
from validator_collection import checkers

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure database
conn = sqlite3.connect("base.db", check_same_thread=False) #seting multithread database
conn.row_factory = sqlite3.Row
db = conn.cursor()



#creating base page
@app.route('/')
def index():
    return render_template("index.html")

#creating page to register
@app.route('/register', methods=["GET", "POST"])
def registr():

    # forget users
    session.clear()

    
    if request.method == "POST":
        #checking are all fields filled up
        if  not request.form.get("login") or not request.form.get("pass") or not request.form.get("name") or not request.form.get("mail"):
            flash("Fill all empty fields!", "Error")
            return render_template('register.html') 
        
        #checking is any user using the same name
        rows = conn.execute("SELECT * FROM users WHERE username LIKE ?", [request.form.get("login")]).fetchall()
        
        if not len(rows) == 0:
            flash("Username is taken, chose another username", "error")
            return render_template("register.html")
        
        #checking is password and confirmation are identical
        if request.form.get("pass") != request.form.get("confirm"):
            flash("Passwords are not identical!", "error")
            return render_template("register.html")
        
        #checking is mail format correct
        mail = request.form.get("mail")   
        if not checkers.is_email(mail):
            flash("Wrong e-mail adress!", "error")
            return render_template("register.html")
        
        #creating insertion to database
        insertion = [
            (request.form.get("login", type=str)),
            (generate_password_hash(request.form.get("pass", type=str),)),
            (request.form.get("name", type=str)),
            mail,
        ]
        
        try:
            conn.execute("INSERT INTO users (username, pass, name, mail) VALUES(?,?,?,?)", insertion)
            conn.commit()
            flash("Registration sucessful \U0001f600")

        except sqlite3.Error as er:
            flash('SQLite error: %s' % (' '.join(er.args)))
            
        user_id = db.execute("SELECT id FROM users WHERE username = ?", [insertion[0]]).fetchall()
        session["user_id"] = user_id[0]["id"]
        
        return render_template("index.html")
                
    else:
        return render_template('register.html')
#rout to loggout user
@app.route('/logout', methods=["GET"])
def logout():
    # Forget any user_id
    session.clear()
    flash("Logged out, I will miss you \U0001F62D")
    # Redirect user to login form
    return redirect("/")

#rout to usersetting
@app.route('/usersetting', methods=["GET", "POST"])
def usersetting():
    if request.method =="POST":

        #changing e-mail adress
        mail = request.form.get("mail", type=str)
        if not mail == "":
            if "@" not in mail or "." not in mail:
                flash("Wrong e-mail adress!", "error")
                return render_template("usersetting.html")
            else:
                insertion = [mail,session["user_id"]]
                try:
                    #updateing new e-mail adress into database
                    conn.execute("UPDATE users SET mail = ? WHERE id = ?", insertion)
                    conn.commit()
                    flash("E-mail adress was changed")

                except sqlite3.Error as er:
                    flash('SQLite error: %s' % (' '.join(er.args)))
                return render_template("usersetting.html")
        else:
            flash("Fill all empty fields!", "Error")
            return render_template("usersetting.html")   
    #deleting accoutn via "GET" method
    else:
        delete = request.args.get("delete")
        #if want to delete account
        if delete == "1":
            question = True
            return render_template("usersetting.html", question = question)
        #if clicked YEST
        elif delete == "YES":
            try:
                #deleting from databese every information about user and clearing the session
                conn.execute("DELETE FROM users WHERE id =?",[session["user_id"]])
                conn.execute("DELETE FROM quest WHERE  quest_id IN (SELECT question FROM connect WHERE user_id = ?)", [session["user_id"]])
                conn.execute("DELETE FROM connect WHERE user_id = ?", [session["user_id"]])
                conn.commit()
                session.clear()
                flash("You account was deleted")
                return render_template("/index.html")
            except sqlite3.Error as er:
                flash('SQLite error: %s' % (' '.join(er.args)))
                return redirect("/usersetting")
        else:
            question = False
            return render_template("usersetting.html")
  
#route to loggin to account
@app.route('/login', methods = ["POST"])
def login():

    #making sure thath session is clear and noone is logged in
    session.clear()

    login = request.form.get("login", type=str)
    rows = db.execute("SELECT * FROM users WHERE username = ?", [login]).fetchall()
    #checking is there only 1 user
    if len(rows) == 1:
        password = check_password_hash(rows[0]["pass"], request.form.get("pass", type=str))
        #checking is password valid
        if password == False: 
            flash("Invalid username and/or password \U0001F973")
            return redirect("/")
    else:
        flash("Invalid username and/or password \U0001F973")
        return redirect("/")
    #seting session to user_id
    session["user_id"] = rows[0]["id"]
    flash("You are logged in \U0001f600")
    return redirect('/')

#rout to creat list of questionnaire
@app.route('/create', methods = ["GET", "POST"])
def create():
       
    if request.method =="POST":
        #checking is field "questionaire Name" was filled up
        if  not request.form.get("questionName"):
            flash("Fill questionaire name!")
            return redirect("/create")
        else:
            #entering to database question Name
            insertion = [session["user_id"], request.form.get("questionName")]
            conn.execute("INSERT INTO connect (user_id, name) VALUES(?,?)", insertion)
            conn.commit()
            return redirect("/create")

    else:
        #makign route to button edit questionaire
        questions = conn.execute("SELECT * FROM connect WHERE user_id = ? ", [session["user_id"]]).fetchall() 
        delete = request.args.get("delete", type = int)
        add = request.args.get("add", type = str)
        if add != None:
            session["quest_id"] = add
            #redirecting to specify questionaire route
            return redirect('/quest')
        #making route to button delete questionaire
        if delete != None:
            try:        
                conn.execute("DELETE FROM connect WHERE (question = ? AND user_id = ?)",[delete, session["user_id"]])
                conn.execute("DELETE FROM quest WHERE quest_id = ?",[delete])
                conn.commit()
                return redirect("/create")
            except sqlite3.Error as er:
                flash('SQLite error: %s' % (' '.join(er.args)))
                return redirect("/create")
            
        else:
            return render_template('create.html', questions = questions, add=add)


@app.route('/quest', methods = ["GET", "POST"])
def quest():
    max_qid = conn.execute("SELECT MAX(q_id) FROM quest WHERE quest_id = ?",[session["quest_id"]]).fetchall()
    renderQuestion = conn.execute("SELECT * FROM quest WHERE quest_id = ? ORDER BY q_id, a_id",[session["quest_id"]]).fetchall()
    if max_qid[0][0] == None:
        session["q_id"] = 1
    else:
        session["q_id"] = int(max_qid[0][0]) + 1
    
    if request.method =="POST":
        if request.form["submitButton"] == "question":
            if request.form.get("question") != "":
                insertion = [
                session["quest_id"],
                session["q_id"],
                "q",
                0,
                request.form.get("question"),
                ]
                try:
                    conn.execute("INSERT INTO quest (quest_id, q_id, type, a_id, txt) VALUES (?,?,?,?,?)", insertion)
                    conn.commit()
                    return redirect('/quest')
                except sqlite3.Error as er:
                    flash('SQLite error: %s' % (' '.join(er.args)))
                    return redirect("/quest")
            else:
                flash("Fill up question field!")
                return redirect("/quest")
        else:
            if request.form.get("answer") != "":
                max_answer = conn.execute("SELECT MAX(a_id) FROM quest WHERE (quest_id = ? AND q_id = ? AND type LIKE ?)",[session["quest_id"], int(request.form["submitButton"]), "a"]).fetchall()
                if max_answer[0][0] == None:
                    a_id = 1
                else:
                    a_id = int(max_answer[0][0]) + 1
                insertion = [
                    session["quest_id"],
                    int(request.form["submitButton"]),
                    "a",
                    a_id,
                    request.form.get("answer")
                ]
                try:
                    conn.execute("INSERT INTO quest (quest_id, q_id, type, a_id, txt) VALUES (?,?,?,?,?)", insertion)
                    conn.commit()
                    return redirect('/quest')
                except sqlite3.Error as er:
                    flash('SQLite error: %s' % (' '.join(er.args)))
                    return redirect("/quest")
            else:
                flash("Fill up answer field!")
                return redirect("/quest")

    else:
        delete = request.args.get("delete", type = int)
        deleteAnswerRequest = request.args.get("deleteAnswer", type = str)
 
        if deleteAnswerRequest != None:
            try:        
                deleteAnswer = deleteAnswerRequest.split("_")
                conn.execute("DELETE FROM quest WHERE (q_id = ? AND quest_id = ? AND a_id = ?)",[int(deleteAnswer[0]), session["quest_id"], int(deleteAnswer[1])])
                print([delete, session["quest_id"]])
                conn.commit()
                return redirect("/quest")
            except sqlite3.Error as er:
                flash('SQLite error: %s' % (' '.join(er.args)))
                return redirect("/quest")
        if delete != None:
            try:        
                conn.execute("DELETE FROM quest WHERE (q_id = ? AND quest_id = ?)",[delete, session["quest_id"]])
                conn.commit()
                return redirect("/quest")
            except sqlite3.Error as er:
                flash('SQLite error: %s' % (' '.join(er.args)))
                return redirect("/quest")
            
        title = conn.execute("SELECT name FROM connect WHERE user_id =? AND question = ?",[session["user_id"], session["quest_id"]]).fetchall()
        
        return render_template('quest.html',renderQuestion = renderQuestion, q = "q", title = title[0][0])


@app.route ("/result_list", methods = ["GET"])
def reult_list():
    
    result = request.args.get("resultView", type = int)
    if result == None: 
        questions = conn.execute("SELECT * FROM connect WHERE user_id = ? ", [session["user_id"]]).fetchall()
        return render_template("/result_list.html", questions = questions)
    else:
        session["result_id"] = result
        return redirect('/result')

@app.route("/result", methods = ["GET"])
def result():

    renderResult = conn.execute("SELECT * FROM quest WHERE quest_id = ? ORDER BY q_id, a_id",[session["result_id"]]).fetchall()
    title = conn.execute("SELECT name FROM connect WHERE user_id =? AND question = ?",[session["user_id"], session["result_id"]]).fetchall()
    
    try:
        submition = int(renderResult[0][5])
        rendered = []
        for row in renderResult:
            dictRow = dict(row)
            dictRow["percentage"] = round((row[5]/submition)*100,2)
            rendered.append(dictRow) 
    except:
        rendered = None
        submition = None

    return render_template("/result.html", renderResult = rendered, q = "q", title = title[0][0], submition = submition)

@app.route("/submition", methods = ["GET", "POST"])
def submition():
    quest_id = request.args.get("q", type = int)
    user_id = request.args.get("u", type = int)
    title = conn.execute("SELECT name FROM connect WHERE user_id =? AND question = ?",[user_id, quest_id ]).fetchall()
    renderQuestions = conn.execute("SELECT * FROM quest WHERE quest_id = ? ORDER BY q_id, a_id",[quest_id]).fetchall()
    dictQuestions = []
    insertion = []
    for row in renderQuestions:
        temp = dict(row)
        dictQuestions.append(temp)

    if request.method == "POST":
        for quest in dictQuestions:
            if quest["type"] == "q":
                result = request.form.get(str(quest["q_id"]))
                if result != None:
                    tempInsertion = {}
                    tempInsertion["q_id"] = quest["q_id"]
                    tempInsertion["a_id"] = result
                    insertion.append(tempInsertion)
                else:
                    flash ("You have to answer all questions")
                    return redirect(f"/submition?q={quest_id}&u={user_id}")
        for answer in insertion:
            conn.execute("UPDATE quest SET result = result + 1 WHERE quest_id = ? AND q_id =? AND a_id = ?",[quest_id, answer["q_id"], answer["a_id"]])
        conn.execute("UPDATE quest SET result = result + 1 WHERE quest_id = ? AND a_id = 0", [quest_id])
        conn.commit()    
        flash("Thank you for your submition \U0001f600")

        # Loading name and e-mail adress
        mailInsertion = conn.execute("SELECT * FROM users WHERE id = ?",[user_id]).fetchall()
        subject = title[0][0]
        name = mailInsertion[0][3]
        smtp_server = "smtp.gmail.com"
        port = 465
        sender = "e-mailadress"   #need to set real address
        receiver = str(mailInsertion[0][4])
        password = "password"    # need to set google key password
        msg = f"""\
From: Questionnaire
To: <{receiver}>
Subject: Your questionnaire {subject} was submited !!    

Hello {name}, someone filled up and submited your questionaire!
Check results in your account:)
        """
        # create secure SSL context
        ssl_pol = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(smtp_server, port, context = ssl_pol) as server:
                server.login(sender, password)
                server.sendmail(sender, receiver, msg)
                server.quit()  
        except:
            print("mail did not send")    
        return redirect("/")

    else:  
        return render_template("submition.html", questions = renderQuestions, q="q", title = title[0][0])




if __name__ == "__main__":
    app.run(debug=True)
