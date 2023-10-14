from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
import connect
import mysql.connector

app = Flask(__name__)
app.secret_key = 'group12'

# Global Variables
dbconn = None
logged_in_user_id = None
logged_in_username = None
logged_in_user_type = None
logged_in_user_type = None
has_active_subscription = False

# Database connection
def getCursor():
    global dbconn
    global connection
    if dbconn == None:
        connection = mysql.connector.connect(user=connect.dbuser,
                                             password=connect.dbpass, host=connect.dbhost,
                                             database=connect.dbname, autocommit=True)
        dbconn = connection.cursor(buffered=True)
        return dbconn
    else:
        return dbconn


# Home page
@app.route("/")
def home():
    global logged_in_user_id
    global logged_in_username
    global logged_in_user_type

    return render_template("home.html")


# User login
@app.route("/login/", methods=['GET', 'POST'])
def login():
    
    # reset the user to default before a new user logs in
    logout_user()  

    if request.method == 'POST':
        username = request.form.get('username')

        # get all active users
        cur = getCursor()
        cur.execute(
            """SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
			FROM user u join usertype ut on u.usertypeid = ut.usertypeid
			WHERE username = %s AND isactive = 1;""", (username,))
        select_result = cur.fetchall()

        login_error = True

        # upon login set the global variables
        if (len(select_result) > 0):
            global logged_in_username
            global logged_in_user_type
            global logged_in_user_id
            logged_in_user_id = select_result[0][0]
            logged_in_username = select_result[0][1]
            logged_in_user_type = select_result[0][2]
            login_error = False

            # set the subscription status globally
            set_subscription_status(logged_in_user_id)

            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', logged_in_username=logged_in_username, logged_in_user_type=logged_in_user_type, login_error=login_error)
   # GET method
    else:  
        return render_template("login.html", logged_in_username=logged_in_username, logged_in_user_type=logged_in_user_type, login_error=False)


# user logout
@app.route("/logout/")
def logout():
    # clear the logged in user details
    logout_user()

    return render_template("login.html")


# dashboard page
# this includes the dashboards for members, trainers and admins
@app.route("/dashboard/")
def dashboard():
    now = datetime.now()
    today_date = datetime.now().date()   

    # get logged in user details
    cur = getCursor()
    cur.execute(
        """SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
		FROM user u join usertype ut on u.usertypeid = ut.usertypeid WHERE userid = %s;""", (logged_in_user_id,))
    select_result = cur.fetchall()

    # get booked classes by current user
    cur = getCursor()
    cur.execute("""SELECT DISTINCT 
                    cm.classname, 
                    DATE(c. startdatetime) as startdate, 
                    c.classid, 
                    e.memberid, 
                    cm.classtype,
                    e.ischeckedin,
                    TIME(c. startdatetime) as starttime
                FROM class c
                JOIN classmaster cm on c.classmasterid = cm.classmasterid
                JOIN enrollment e on c.classid=e.classid
                JOIN user u on u.userid=e.memberid
                WHERE userid = %s 
                AND c.startdatetime BETWEEN %s AND DATE_ADD(%s, INTERVAL 12 HOUR);""",
        (logged_in_user_id, now, now))
    bookedclass = cur.fetchall()
    
    if (len(select_result) > 0):
        # get all trainer details
        cur.execute("""SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
		FROM user u inner join usertype ut on u.usertypeid = ut.usertypeid WHERE ut.usertypename = 'trainer';""")
        trainerList = cur.fetchall()

        # get all future classes details
        # and check if the logged in user has already booked the class
        # also get the capacity left for the class
        cur.execute(
            """
                SELECT 
                    cm.classname, 
                    u.firstname, 
                    u.familyname, 
                    r.roomname, 
                    DATE(c.startdatetime) as startdate, 
                    TIME(c.startdatetime) as starttime, 
                    (r.capacity - (SELECT COUNT(enrollmentid) FROM enrollment e WHERE e.classid = c.classid)) AS spaceLeft, 
                    c.classid, 
                    c.roomid,
                    CASE WHEN (SELECT COUNT(*) FROM enrollment WHERE memberid = %s AND classid = c.classid) > 0 THEN 1 ELSE 0 END AS isbooked
                FROM class c
                JOIN classmaster cm on c.classmasterid = cm.classmasterid				
                JOIN user u ON c.trainerid = u.userid 
                JOIN room r ON c.roomid = r.roomid 
                WHERE classtype = 'Exercise Class' 
                AND c.startdatetime > NOW() 
                ORDER BY cm.classtype ASC, c.startdatetime ASC;
                """, (logged_in_user_id,))
        classList = cur.fetchall()

        # get subscription details
        cur = getCursor()
        sql_get_subscription = """  SELECT S.memberid, S.startdate, S.enddate FROM subscription S
                                JOIN user U on U.userid = S.memberid
                                WHERE S.memberid = %s
                                ORDER BY startdate DESC
                                LIMIT 1;"""

        cur.execute(sql_get_subscription, (logged_in_user_id,))
        get_subscription_result = cur.fetchall()

        subscription = None

        if (len(get_subscription_result) > 0):
            subscription = get_subscription_result[0]     

        # check if the subscription is about to expire
        date_diff = None
        if subscription: 
            end_date=subscription[2]
            date_diff=end_date-today_date
            if date_diff < timedelta(days=14):
                flash("Please renew your subscription.")

        # check if the user has already attended the class today      
        cur.execute(
            "SELECT COUNT(*) FROM attendance WHERE memberid = %s AND datetimeattended = CURDATE()", (logged_in_user_id,)
        )

        select_attendance = cur.fetchall()

        attendance = False

        if (len(select_attendance) > 0):
            if (select_attendance[0][0] > 0):
                attendance = True
        
        # get the news updates to show on the dashboard
        # this will be shown only for members and trainers
        cur.execute("""SELECT
                        newsid,
                        title,
                        newsdetail,
                        newsdate,
                        CONCAT(U.firstname, ' ', U.familyname) AS authorname
                        FROM news N
                        JOIN user U ON U.userid = N.authorid
                        WHERE N.isactive = 1
                        AND issent = 1
                        ORDER BY newsdate DESC;""")
        
        select_news = cur.fetchall()

        news = None

        if (len(select_news) > 0):
            news = select_news

        # get classes for trainers 
        trainer_classes = get_classes_for_trainer(
            logged_in_user_id, "Exercise Class")

        # get specialised training for trainers
        trainer_specialised_training = get_classes_for_trainer(
            logged_in_user_id, "Specialised Training")

        return render_template("dashboard.html", 
                               user=select_result[0], 
                               bookedclass=bookedclass, 
                               classList=classList, 
                               trainerList=trainerList, 
                               trainer_classes=trainer_classes,
                               specialised_training=trainer_specialised_training,
                               subscription=subscription,
                               attendance=attendance,
                               today_date=today_date,
                               datediff=date_diff,
                               news = news,
                               has_active_subscription=has_active_subscription,)


# member checks in to class
@app.route("/dashboard/membercheckinclass/", methods=['GET', 'POST'])
def member_check_in_class():
    class_id = request.form.get('class_id')
    member_id = logged_in_user_id
    
    cur = getCursor()    
    cur.execute(
        "INSERT INTO attendance (classid,memberid) VALUES (%s,%s);", (class_id, member_id))
    cur.execute(
        "UPDATE enrollment SET ischeckedin = 1 WHERE classid = %s AND memberid = %s;", (class_id, member_id))
    
    flash("Checked in successfully!")

    return redirect("/dashboard/")


# member checks in to gym for general use
@app.route("/dashboard/membercheckingym/", methods=['GET', 'POST'])
def member_check_in_gym():
    todaydate = datetime.now().date()
    gym_id = request.form.get('gym_id')
    member_id = logged_in_user_id
    cur = getCursor()
    cur.execute("INSERT INTO attendance (classid,memberid,datetimeattended) VALUES (%s,%s,%s);",
                (gym_id, member_id, todaydate))
    
    flash("Checked in successfully!")

    return redirect("/dashboard/")


# update user by manager or user themselves
@app.route("/user/update/", methods=['GET', 'POST'])
def update_user():
    if request.method == 'POST':
        # get the values from the update form
        user_id = request.form.get('user_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')
        house_number_name = request.form.get('house_number_name')
        street = request.form.get('street')
        town = request.form.get('town')
        city = request.form.get('city')
        postal_code = request.form.get('postal_code')


        cur = getCursor()

        sql_update_user = """UPDATE user 
                            SET firstname = %s, 
                            familyname = %s,
                            dateofbirth = %s, 
                            housenumbername = %s, 
                            street = %s, 
                            town = %s,
                            city = %s,
                            postalcode = %s
                            WHERE userid = %s;"""

        parameters = (first_name, last_name, date_of_birth, house_number_name,
                      street, town, city, postal_code, user_id,)

        cur.execute(sql_update_user, parameters)

        flash("User updated successfully!")
        return redirect("/dashboard/")
    # navigate to the update user page
    else:
        user_id = request.args.get('user_id')

        if logged_in_username is not None:
            cur = getCursor()
            cur.execute(
                """SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
				FROM user u join usertype ut on u.usertypeid = ut.usertypeid WHERE userid = %s;""", (user_id,))
            select_result = cur.fetchall()

            if (len(select_result) > 0):
                if (str(logged_in_user_id) == user_id or logged_in_user_type == "admin"):
                    return render_template("update_user.html", user=select_result[0], authorized=True)
                else:
                    return render_template("update_user.html", authorized=False)
        else:
            return redirect(url_for("login"))


# logout user
# this will reset all the global variables to default
def logout_user():
    global logged_in_user_id
    global logged_in_username
    global logged_in_user_type
    global has_active_subscription

    logged_in_user_id = None
    logged_in_username = None
    logged_in_user_type = None
    has_active_subscription = False


# admin search for a member to manage their details
@app.route("/admin/manage_member/", methods=["GET", "POST"])
def search_member():
    todaydate = datetime.now().date()
    # default page load shows all the members 
    if request.method == 'GET':
        cur = getCursor()
        cur.execute("""
            SELECT userid, username, firstname, familyname, dateofbirth, housenumbername, street, town, 
                    city, postalcode, MAX(s.enddate) as maxenddate, u.isactive
            FROM user u
            JOIN usertype ut on u.usertypeid = ut.usertypeid
            LEFT JOIN subscription s
            ON u.userid = s.memberid
            WHERE ut.usertypename = 'member'
            GROUP BY u.userid, ut.usertypename;"""
            )
        members = cur.fetchall()
        return render_template("search_member.html", members=members, todaydate=todaydate)
    # search member by username, firstname, familyname or fullname
    elif request.method == "POST":
        member_name = request.form.get("search")
        member_name = member_name if member_name else ""
        member_name = "%" + member_name + "%"
        cur = getCursor()
        cur.execute(
            """SELECT userid, username, firstname, familyname, dateofbirth, housenumbername, street, town, 
            city, postalcode, MAX(s.enddate) as maxenddate, u.isactive
            FROM user u 
			JOIN usertype ut on u.usertypeid = ut.usertypeid
            LEFT JOIN subscription s ON u.userid = s.memberid
            WHERE (userid LIKE %s 
                    OR u.username LIKE %s
                    OR u.firstname LIKE %s 
                    OR u.familyname LIKE %s 
                    OR CONCAT(u.firstname, ' ', u.familyname) LIKE %s) 
            AND ut.usertypename = 'member'
            GROUP BY u.userid, ut.usertypename;""",
            (member_name, member_name, member_name, member_name, member_name),
        )
        column_names = [desc[0] for desc in cur.description]
        searchedmember = cur.fetchall()

        return render_template(
            "search_member.html", members=searchedmember, dbcol=column_names, todaydate=todaydate
        )
    else:
        # check if user is logged in and is an admin
        if logged_in_username is not None and logged_in_user_type == "admin":
            return render_template("search_member.html")
        else:
            return redirect(url_for("login"))


# add a new member
@app.route("/admin/add_new_member/")
def add_new_member():
    # check if user is logged in and is an admin
    if logged_in_username is not None and logged_in_user_type == "admin":
        return render_template("add_new_member.html")
    else:
        return redirect(url_for("login"))


# save member details
@app.route("/admin/add_new_member_db/", methods=['GET', 'POST'])
def add_new_member_db():
    todaydate = datetime.now().date()
    todaydate_str = todaydate.strftime("%Y-%m-%d")
    todaydate = datetime.strptime(todaydate_str, "%Y-%m-%d")
    username = request.form.get("username")
    firstname = request.form.get("firstname").capitalize()
    familyname = request.form.get("familyname").capitalize()
    dateofbirth = request.form.get("dateofbirth")
    dateofbirth = datetime.strptime(dateofbirth, "%Y-%m-%d")
    housenumbername = request.form.get("housenumbername").capitalize()
    street = request.form.get("street").capitalize()
    town = request.form.get("town").capitalize()
    city = request.form.get("city").capitalize()
    postalcode = request.form.get("postalcode")
    cur = getCursor()
    cur.execute(
        """SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
		FROM user u join usertype ut on u.usertypeid = ut.usertypeid WHERE username = %s;""", (username,))
    
    # check if username is already taken
    # and display an error message
    select_result = cur.fetchall()

    if (len(select_result) > 0):
        flash("The username is already taken. Please choose another name.")
        return redirect('/admin/add_new_member/')
    
    # the system currently only allows members to be 18 years old or above
    if todaydate.year - dateofbirth.year < 18:
        flash("Member must be 18 years old or above!")
        return redirect('/admin/add_new_member/')
    else:
        cur.execute("""
    INSERT INTO user(
        username,
        usertypeid,
        firstname, 
        familyname, 
        dateofbirth, 
        housenumbername, 
        street, 
        town, 
        city, 
        postalcode,
        isactive)
    VALUES(%s,'3',%s,%s,%s,%s,%s,%s,%s,%s,1);""",
                    (username, firstname, familyname, dateofbirth, housenumbername, street, town, city, postalcode,))
    flash("Member added successfully!")

    return redirect("/dashboard/")


# admin view trainers' classes/ search and result page
@app.route("/admin/view_trainer_classes_search/", methods=['GET', 'POST'])
def search_trainer():
    if logged_in_username is not None and logged_in_user_type == 'admin':
        if request.method == 'GET':
            cur=getCursor()
            cur.execute("""SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
			FROM user u join usertype ut on u.usertypeid = ut.usertypeid WHERE ut.usertypename = 'trainer'""")
            trainerList = cur.fetchall()
            return render_template('search_trainer.html', trainerlist=trainerList)
        elif request.method == 'POST':
            trainer = request.form.get("trainer")
            if trainer == None or trainer.strip() == "":
                return render_template('search_trainer.html', trainer=None, trainerlist=[])
            elif "%" in trainer:
                trainerterm = trainer.replace("%", "")
            else:
                trainerterm = "%" + trainer + "%"

            cur = getCursor()
            cur.execute("""
            SELECT u.userid, u.username, ut.usertypename, u.firstname, u.familyname, u.dateofbirth, u.housenumbername, u.street, u.town, u.city, u.postalcode, u.isactive 
			FROM user u join usertype ut on u.usertypeid = ut.usertypeid WHERE ut.usertypename = 'trainer' AND (CONCAT(firstname, familyname) LIKE %s 
            OR CONCAT(firstname, " ", familyname) LIKE %s OR userid LIKE %s);
            """, (trainerterm, trainerterm, trainerterm,))
            trainerList = cur.fetchall()
            return render_template("search_trainer.html", trainer=trainer, trainerlist=trainerList)
    else:
        return redirect(url_for("login"))


# view trainers' classes
# the list will show all classes first, and can filter classes
@app.route("/admin/view_trainer_classes/<trainer>/")
@app.route("/admin/view_trainer_classes/<trainer>/<filter>")
def view_trainer_classes(trainer, filter='all'):
    if logged_in_username is not None and logged_in_user_type == 'admin':
        cur = getCursor()
        if filter == 'all':
            cur.execute("""SELECT username,  
            c.classid,cm.classname, cm.classtype, c.roomid, r.roomname, 
            DATE(c.startdatetime) as startdate,
            TIME(c.startdatetime) as starttime,
            DATE(c.enddatetime) as enddate,
            TIME(c.enddatetime) as endtime
            FROM class c
            JOIN classmaster cm on c.classmasterid = cm.classmasterid		
            JOIN user u ON u.userid=c.trainerid
            JOIN room r ON r.roomid=c.roomid
            WHERE username = %s OR trainerid = %s
            ORDER BY c.startdatetime
            """, (trainer, trainer,))
        if filter == '7':
            cur.execute("""SELECT username,  
            c.classid,cm.classname, cm.classtype, c.roomid, r.roomname, 
            DATE(c.startdatetime) as startdate,
            TIME(c.startdatetime) as starttime,
            DATE(c.enddatetime) as enddate,
            TIME(c.enddatetime) as endtime
            FROM class c 
            JOIN classmaster cm on c.classmasterid = cm.classmasterid		
            JOIN user u ON u.userid=c.trainerid
            JOIN room r ON r.roomid=c.roomid
            WHERE username = %s OR trainerid = %s
            HAVING DATE(startdate) BETWEEN DATE(NOW()) AND DATE_ADD(DATE(NOW()), INTERVAL 7 DAY)
            ORDER BY startdate;
            """, (trainer, trainer,))
        if filter == '14':
            cur.execute("""SELECT username,  
            c.classid,cm.classname, cm.classtype, c.roomid, r.roomname, 
            DATE(c.startdatetime) as startdate,
            TIME(c.startdatetime) as starttime,
            DATE(c.enddatetime) as enddate,
            TIME(c.enddatetime) as endtime
            FROM class c
            JOIN classmaster cm on c.classmasterid = cm.classmasterid			
            JOIN user u ON u.userid=c.trainerid
            JOIN room r ON r.roomid=c.roomid
            WHERE username = %s OR trainerid = %s
            HAVING DATE(startdate) BETWEEN DATE(NOW()) AND DATE_ADD(DATE(NOW()), INTERVAL 14 DAY)
            ORDER BY startdate;
            """, (trainer, trainer,))
        if filter == '21':
            cur.execute("""SELECT username,  
            c.classid,cm.classname, cm.classtype, c.roomid, r.roomname, 
            DATE(c.startdatetime) as startdate,
            TIME(c.startdatetime) as starttime,
            DATE(c.enddatetime) as enddate,
            TIME(c.enddatetime) as endtime
            FROM class c
            JOIN classmaster cm on c.classmasterid = cm.classmasterid					
            JOIN user u ON u.userid=c.trainerid
            JOIN room r ON r.roomid=c.roomid
            WHERE username = %s OR trainerid = %s
            HAVING DATE(startdate) BETWEEN DATE(NOW()) AND DATE_ADD(DATE(NOW()), INTERVAL 21 DAY)
            ORDER BY startdate;
            """, (trainer, trainer,))
        classes = cur.fetchall()
        return render_template('admin_view_trainer_class.html', classes=classes, trainer=trainer)
    else:
        return redirect(url_for("login"))


# admin updates member details
@app.route("/admin/manage_member/edit/<userid>", methods=['GET', 'POST'])
def edit_member(userid):
    if request.method == 'POST':
        print(userid)
        firstname = request.form.get("first_name")
        familyname = request.form.get("last_name")
        dateofbirth = request.form.get("date_of_birth")
        housenumbername = request.form.get("house_number_name")
        street = request.form.get("street")
        town = request.form.get("town")
        city = request.form.get("city")
        postalcode = request.form.get("postal_code")
        print(firstname)
        cur = getCursor()
        sql = """UPDATE user SET 
                firstname=%s, 
                familyname=%s, 
                dateofbirth=%s,
                housenumbername=%s,
                street=%s,
                town=%s,
                city=%s,
                postalcode=%s
                WHERE userid=%s;"""
        cur.execute(sql, (firstname, familyname, dateofbirth, housenumbername,
                    street, town, city, postalcode, userid))
        flash("Member updated successfully!")

        return redirect("/dashboard/")
    else:
        # get member details for editing
        select_result = get_user_by_user_id(userid)        

        return render_template("edit_member.html",user=select_result[0])


# view member details
@app.route("/view_member/<userid>")
def view_member(userid):
    if logged_in_username is not None and (logged_in_user_type == 'admin' or logged_in_user_type == 'trainer'):
        # get member details
        select_result = get_user_by_user_id(userid)
        
        return render_template("view_member.html",member=select_result[0])
    else:
        return redirect(url_for("login"))


# view individual trainer based on their userid
# if the member isn't subscribed, they cannot make bookings for classes
@app.route("/member/viewtrainer/<userid>", methods=['GET','POST'])
def view_trainer(userid):
        
        if logged_in_username is not None and logged_in_user_type == 'member':
            if request.method == 'GET':

                # get trainer details including their training and 
                # also get capacity and spaces left for each class
                cur = getCursor()
                cur.execute("""
                    SELECT
                        trainerid,  
                        classname,
                        roomname,
                        CONCAT(firstname, ' ' , familyname) as trainername,
                        fee, 
                        DATE(startdatetime) as startdate,
                        TIME(startdatetime) as starttime,
                        capacity,
                        capacity - (SELECT COUNT(*) FROM enrollment WHERE classid = C.classid) AS spacesleft,
                        C.classid,
                        CASE WHEN (
							SELECT COUNT(*) 
                            FROM enrollment 
                            WHERE memberid = %s 
                            AND classid = C.classid
                            AND isactive = 1) > 0 THEN 1 ELSE 0 END AS booked
                    FROM class C
                    JOIN classmaster CM on C.classmasterid = CM.classmasterid		
                    JOIN user U ON U.userid = C.trainerid
                    JOIN room R ON R.roomid = C.roomid
                    WHERE U.userid = %s
                        AND CM.classtype = 'Specialised Training'
                        AND C.startdatetime >= NOW();""", 
                    (logged_in_user_id, userid,)
                )
                trainings = cur.fetchall()

                if(len(trainings) == 0):
                    trainings = None
                
                # get subscription details
                cur = getCursor()
                cur.execute("""
                    SELECT 
                        S.subscriptionid,
                        P.method,
                        P.bankname,
                        P.accountnumber,
                        P.cardnumber
                    FROM subscription S
                    JOIN payment P ON P.paymentid = S.paymentid
                    WHERE memberid = %s
                    AND isactive = 1;""", (logged_in_user_id,))
                
                subscription = cur.fetchall()

                if (len(subscription) == 0):
                    subscription = None
                
                return render_template('members_view_trainer_class.html', 
                    trainings=trainings,
                    has_active_subscription=has_active_subscription,
                    subscription=subscription)

            # book training session
            else:
                memberid=logged_in_user_id
                classid=request.form.get("classid") 
                
                # get subscription paymentid
                cur = getCursor()
                cur.execute("""SELECT paymentid 
                            FROM subscription 
                            WHERE memberid = %s AND isactive = 1;""", (memberid,))
                
                paymentid = cur.fetchall()[0][0]

                # get cancelled bookings 
                cur = getCursor()
                cur.execute("""SELECT * FROM enrollment
                            WHERE memberid = %s
                            AND classid = %s
                            AND isactive = 0 OR isactive IS NULL;""", (memberid, classid,))
                
                cancelled_booking = cur.fetchall()

                # if there is a cancelled booking, update it
                if len(cancelled_booking) > 0:
                    cur = getCursor()
                    cur.execute("""UPDATE enrollment SET isactive = 1
                                WHERE memberid = %s
                                AND classid = %s
                                AND isactive = 0 OR isactive IS NULL;""", (memberid, classid,))
                    flash("You have booked training session successfully!")
                    return redirect("/dashboard/")
                # otherwise insert a new booking
                else: 
                    cur=getCursor()
                    cur.execute("""INSERT INTO enrollment (classid, memberid, paymentid, isactive) 
                                VALUES(%s,%s,%s,%s);""", (classid, memberid, paymentid, 1,))
                    flash("You have booked training session successfully!")
                    return redirect("/dashboard/")
        else:
            return redirect(url_for("login"))


# cancel booking
@app.route("/member/cancel_booking/<classid>", methods=['POST'])
def cancel_booking(classid):
    if logged_in_username is not None and logged_in_user_type == 'member':
        
        # members cancel bookings made by themselves
        cur = getCursor()
        cur.execute("""UPDATE enrollment 
                    SET isactive = 0 
                    WHERE classid = %s 
                    AND memberid = %s""",
                    (classid, logged_in_user_id,)
                    )

        flash("You have cancelled booking successfully!")

        return redirect("/dashboard/")
    else:
        return redirect(url_for("login"))


# activate/ deactivate member
@app.route("/admin/manage_member/deactivate/<userid>", methods=["POST"])
def admin_deactivate_member(userid):

    # check if user is active
    cur = getCursor()
    cur.execute("SELECT isactive FROM user WHERE userid = %s", (userid,))

    isactive = cur.fetchall()[0][0]

    if isactive == 1:
        flashmessage = "Member deactivated successfully!"
        isactive = 0
    else:
        flashmessage = "Member activated successfully!"
        isactive = 1

    # activate or deactivate based on current status
    cur = getCursor()
    cur.execute("UPDATE user set isactive = %s WHERE userid = %s", (isactive, userid,))

    flash(flashmessage)

    return redirect("/dashboard/")


# subscription page
@app.route("/subscription", methods=['GET', 'POST'])
def subscription():

    if request.method == 'GET':
        user_id = request.args.get("user_id")
        add_subscription = request.args.get("add_subscription")

        # get subscription and payment details for a member
        cur = getCursor()
        cur.execute("""
                    SELECT 
                        S.memberid, 
                        S.startdate, 
                        S.enddate,
                        P.method,
                        P.bankname,
                        P.accountnumber,
                        SUBSTRING(P.cardnumber, -4) AS cardnumber
                    FROM subscription S
                    JOIN user U on U.userid=S.memberid
                    JOIN payment P on P.paymentid=S.paymentid
                    WHERE S.memberid = %s
                    ORDER BY startdate DESC
                    LIMIT 1
                    """, (user_id,))
        subscription = cur.fetchall()

        if (len(subscription) == 0):
            subscription = None

        authorized = False
        subscription_fee = get_subscription_fee()

        # restrict access to admin and current member user
        if (str(logged_in_user_id) == user_id or logged_in_user_type == 'admin'):
            authorized = True

        return render_template('subscription.html',
                                subscription=subscription,
                                add_subscription=add_subscription,
                                authorized=authorized,
                                subscription_fee = get_subscription_fee(),
                                today_date=datetime.now().date(),
                                member_id=user_id)


# add subscription and make payment
@app.route("/subscription/add", methods=['POST'])
def add_subscription():

    todaydate = datetime.now().date()

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        payment_method = request.form.get('payment_method')
        card_name = request.form.get('card_name')
        card_number = request.form.get('card_number')
        card_expiration = request.form.get('card_expiration')
        card_cvv = request.form.get('card_cvv')
        bank_name = request.form.get('bank_name')
        account_number = request.form.get('account_number')
        start_date = request.form.get('start_date')
        start_date_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_date = start_date_date + timedelta(days=30)
        end_date = end_date_date.strftime('%Y-%m-%d')

        if (payment_method == "credit_card"):
            payment_method = "Credit Card"
        elif (payment_method == "bank_account"):
            payment_method = "Bank Transfer"

        # save cvv field as 0 if it is empty to avoid error
        if (card_cvv == '' or card_cvv == None):
            card_cvv = 0

        # add new payment to payment table
        cur = getCursor()
        cur.execute("""INSERT INTO payment (
                        userid,
                        method,
                        amount,
                        bankname,
                        accountnumber,
                        cardname,
                        cardnumber,
                        cardexpirydate,
                        cardcvv,
                        paymentdate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (member_id,
                     payment_method, 
                     get_subscription_fee(), 
                     bank_name, 
                     account_number, 
                     card_name, 
                     card_number,
                     card_expiration,
                     card_cvv,
                     todaydate,)
                     )
        payment_id_added = cur.lastrowid

        # add new subscription to subscription table
        cur = getCursor()
        cur.execute("""INSERT INTO subscription (memberid, startdate, enddate, paymentid, isactive) VALUES (%s, %s, %s, %s, %s)""",
                    (member_id, start_date, end_date, payment_id_added, 1))

        flash("Subscription added successfully!")

        # set subscription status globally
        set_subscription_status(member_id)

        if(logged_in_user_type == "member"):
            return redirect("/subscription?user_id=" + str(logged_in_user_id) + "&add_subscription=0")
        else:
            return redirect("/dashboard/")


# renew subscription
@app.route("/subscription/renew", methods=['POST'])
def renew_subscription():

    start_date = request.form.get('start_date')
    start_date_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_date = start_date_date + timedelta(days=30)
    end_date = end_date_date.strftime('%Y-%m-%d')

    # get the payment id of the previous subscription
    cur = getCursor()
    cur.execute("""SELECT paymentid FROM subscription WHERE memberid = %s ORDER BY enddate DESC LIMIT 1;""",
                (logged_in_user_id,))
    payment_id = cur.fetchone()[0]

    # add new subscription to subscription table
    cur = getCursor()
    cur.execute("""INSERT INTO subscription (memberid, startdate, enddate, paymentid, isactive) VALUES (%s, %s, %s, %s, %s)""",
                (logged_in_user_id, start_date, end_date, payment_id, 1))
    
    # deactivate previous subscriptions
    cur.execute("""UPDATE subscription SET isactive = 0 WHERE memberid = %s AND isactive = 1 AND enddate < NOW()""",
                (logged_in_user_id,))

    flash("Subscription renewed successfully!")

    # set subscription status globally
    set_subscription_status(logged_in_user_id)

    return redirect("/subscription?user_id=" + str(logged_in_user_id) + "&add_subscription=0")


# admin views attendance report
@app.route("/admin/view_attendance/", methods=['GET',"POST"])
def view_attendance():
    if request.method == 'GET':

        # get attendance details for all classes and trainings
        cur = getCursor()
        cur.execute("""SELECT 
                            c.classid, 
                            cm.classname, 
                            cm.classtype, 
                            r.roomname, 
                            DATE(c.startdatetime),
                            TIME(c.startdatetime),
                            COUNT(u.userid) as "number of attendees", 
                            c.classid 
                        FROM user u
                        join attendance a on a.memberid=u.userid
                        join class c on c.classid=a.classid
						join classmaster cm on c.classmasterid = cm.classmasterid
                        join room r on r.roomid=c.roomid
                        where cm.classtype!='Self Training'
                        group by cm.classname, c.classid, r.roomname""")
        fullattendance = cur.fetchall()

        # get attendance details for general gym use
        cur.execute("""
                    SELECT 
                        cm.classtype, 
                        r.roomname, 
                        DATE(a.datetimeattended),
                        TIME(a.datetimeattended),
                        COUNT(u.userid) as "number of attendees" 
                    FROM attendance a
                        Join user u  on a.memberid=u.userid
                        join class c on c.classid=a.classid
						join classmaster cm on c.classmasterid = cm.classmasterid
                        join room r on r.roomid=c.roomid
                        where cm.classtype='Self Training'
                        group by a.datetimeattended, r.roomname""")
        generalattendance = cur.fetchall()

        return render_template('admin_view_members_attendance.html', attendanceList=fullattendance, gymattendance=generalattendance)
    
    # POST request
    else: 
        time_a=request.form.get('time_a')
        time_b=request.form.get('time_b')
        print(time_a)
        print(time_b)

        # get attendance details for all classes and trainings for given time period
        cur = getCursor()
        cur.execute("""SELECT c.classid, cm.classname, cm.classtype, r.roomname, c.startdatetime,
                        COUNT(u.userid) as 'number of attendees' FROM user u
                        Join attendance a on a.memberid=u.userid
                        join class c on c.classid=a.classid
						join classmaster cm on c.classmasterid = cm.classmasterid
                        join room r on r.roomid=c.roomid
                        where cm.classtype!='Self Training' 
                        and c.startdatetime<= DATE_ADD(%s, INTERVAL 1 day) AND c.startdatetime>=%s
                        group by cm.classname, c.classid, r.roomname;""", (time_b, time_a,))
        attendance = cur.fetchall()

        # get attendance details for general gym use for given time period
        cur.execute("""SELECT  cm.classtype, r.roomname, a.datetimeattended,
                        COUNT(u.userid) as "number of attendees" FROM attendance a
                        Join user u  on a.memberid=u.userid
                        join class c on c.classid=a.classid
						join classmaster cm on c.classmasterid = cm.classmasterid
                        join room r on r.roomid=c.roomid
                        where cm.classtype='Self Training'
                        and a.datetimeattended<=%s AND a.datetimeattended>=%s
                        group by a.datetimeattended,r.roomname""", (time_b, time_a,))
        generalgymattendance = cur.fetchall()
        return render_template('admin_view_members_attendance.html', attendanceList=attendance, gymattendance=generalgymattendance) 


# view attendees for selected class/ training
@app.route("/admin/view_attendance/<classid>", methods=["GET"])
def classes_training_attendance(classid):
    cur = getCursor()
    cur.execute("""select u.firstname, u.familyname, cm.classname, c.startdatetime from user u
                    join attendance a on a.memberid=u.userid
                    join class c on c.classid=a.classid
					join classmaster cm on c.classmasterid = cm.classmasterid
                    where c.classid= %s""",(classid,))
    attendeelist = cur.fetchall()
    return render_template('classes_training_attendance.html', attendee_List=attendeelist) 


# view gym attendees for a given date
@app.route("/admin/gym_attendees/<datetimeattended>", methods=["GET"])
def gym_attendees(datetimeattended):
    cur = getCursor()
    cur.execute("""select u.firstname, u.familyname, a.datetimeattended from user u
                    join attendance a on a.memberid=u.userid
                    join class c on c.classid=a.classid
                    where a.datetimeattended=%s""",(datetimeattended,))
    gym_attendee = cur.fetchall()
    return render_template('gym_attendees.html', attendee_gym=gym_attendee)


# members book exercise classes
@app.route("/dashboard/member/bookclass/", methods=['GET', 'POST'])
def book_class():

    memberid = int(request.form.get('user_id'))
    classid = int(request.form.get('class_id'))

    cur = getCursor()

    sql_add_enrollment = """INSERT INTO enrollment(classid, memberid, isactive)VALUES(%s,%s,%s);"""
    parameters = (classid, memberid, 1,)
    cur.execute(sql_add_enrollment, parameters)

    flash("You have booked exercise class successfully!")
    return redirect("/dashboard/")


# view list of members that needs to process payments
@app.route("/admin/process_payment", methods=["GET", "POST"])
def admin_process_payment():
    member_name = request.form.get("search")
    member_name = member_name if member_name else ""
    member_name = "%" + member_name + "%"
    cur = getCursor()
    cur.execute(
        """SELECT 
            userid, 
            firstname, 
            familyname, 
            enddate 
        FROM user u
		JOIN usertype ut on u.usertypeid = ut.usertypeid
        LEFT JOIN subscription 
        ON u.userid = subscription.memberid 
        WHERE (u.isactive = 1 AND ut.usertypename = 'member') 
        AND (u.userid LIKE %s 
            OR firstname LIKE %s 
            OR familyname LIKE %s 
            OR CONCAT(firstname, ' ', familyname) LIKE %s) 
        AND paymentid IS NULL
        ORDER BY enddate;""",
        (member_name, member_name, member_name, member_name),
    )
    column_names = [desc[0] for desc in cur.description]
    searchedmembersubscription = cur.fetchall()

    # check if user is logged in and is an admin
    if logged_in_username is not None and logged_in_user_type == "admin":
        return render_template(
            "admin_process_payment.html",
            membersubscription=searchedmembersubscription,
            dbcol=column_names,
        )
    else:
        return redirect(url_for("login"))


# news/ updates - view and add news functions for admin
@app.route("/admin/news", methods=['GET', 'POST'])
def news():
    # view news
    if request.method == 'GET':

        # check if user is logged in and is an admin
        if(logged_in_user_type != "admin"):
            return redirect(url_for("login"))
        
        # get news from database and display it in admin news page
        # only shows the first 50 characters of the news detail
        cur = getCursor()
        cur.execute(
            """SELECT 
            newsid, title, newsdetail, newsdate, authorid, issent, 
            N.isactive, CONCAT(U.firstname, ' ', U.familyname) as authorname,
            CASE WHEN LENGTH(newsdetail) > 50 THEN CONCAT(SUBSTRING(newsdetail, 1, 50), '...') ELSE newsdetail END as newsdetailshort
            FROM news N
            JOIN user U on U.userid=N.authorid
            WHERE U.userid = %s AND N.isactive = 1
            ORDER BY newsdate DESC
            """, (logged_in_user_id,))

        select_result = cur.fetchall()

        news = None

        if (len(select_result) > 0):
            news = select_result

        return render_template('news.html', authorized=True, news=news)
    
    # POST request - add news
    else:
        news_title = request.form.get("news_title")
        news_date = request.form.get("news_date")
        news_detail = request.form.get("news_detail")
        news_author_id = logged_in_user_id

        cur = getCursor()
        sql = """INSERT INTO news (title, newsdate, newsdetail, authorid, issent, isactive) VALUES (%s, %s, %s, %s , 0, 1);"""
        cur.execute(sql, (news_title, news_date,
                    news_detail, news_author_id,))
        flash("News added successfully!")
        return redirect("/admin/news")


# news/ updates - delete news function for admin
@app.route("/admin/delete_news")
def delete_news():
    news_id = request.args.get("news_id")
    cur = getCursor()
    update_news_query = """UPDATE news SET isactive = 0 WHERE newsid = %s;"""
    cur.execute(update_news_query, (news_id,))

    flash("News deleted successfully!")

    return redirect("/admin/news")


# news/ updates - send news function for admin
@app.route("/admin/send_news")
def send_news():
    news_id = request.args.get("news_id")
    cur = getCursor()
    update_news_query = """UPDATE news SET issent = 1 WHERE newsid = %s;"""
    cur.execute(update_news_query, (news_id,))

    flash("News sent successfully!")

    return redirect("/admin/news")


# admin view popular class
@app.route("/admin/popular_class")
def view_popular_class():
    cur = getCursor()
    cur.execute("""select a.classid, cm.classname, u.firstname, u.familyname, date_format(c.startdatetime, '%d/%m/%y') as 'date',date_format(c.startdatetime, '%H:%i:%s') as 'time',count(memberid) from attendance a join class c on a.classid = c.classid 
	join classmaster cm on c.classmasterid = cm.classmasterid
	join user u on c.trainerid = u.userid where cm.classtype = "Exercise Class" group by classid order by count(memberid) desc;""")
    popular_class = cur.fetchall()
    cur.execute("""select e.classid, cm.classname, u.firstname, u.familyname, date_format(c.startdatetime, '%d/%m/%y') as 'date',date_format(c.startdatetime, '%H:%i:%s') as 'time', count(memberid) from enrollment e join class c on e.classid = c.classid 
	join classmaster cm on c.classmasterid = cm.classmasterid
	join user u on c.trainerid = u.userid where cm.classtype = "Exercise Class" group by classid order by count(memberid) desc;""")
    mostbooked_class = cur.fetchall()
    return render_template("admin_view_popular_class.html", popular_class=popular_class, mostbooked_class=mostbooked_class)


# view financial report
@app.route("/admin/view_financial_report", methods=['GET'])
def view_financial_report():

    subscription_fee = get_subscription_fee()
    
    cur = getCursor()
    cur.execute("""select count(*) as subno, count(*) * %s as subfees from subscription s 
		inner join user u on s.memberid = u.userid
		join usertype ut on u.usertypeid = ut.usertypeid
		where ut.usertypename = 'member' and s.enddate > DATE_ADD(NOW(), INTERVAL -DAY(NOW())+1 DAY)""", (subscription_fee,))
    
    subfeeslist = cur.fetchall()

    cur.execute("""select count(*) as stno, count(*) * %s as stfees from class c
	join classmaster cm on c.classmasterid = cm.classmasterid	
	where classid in (select distinct classid from enrollment) 
	and cm.classtype = 'Specialised Training'
    and c.startdatetime >= DATE_ADD(NOW(), INTERVAL -DAY(NOW())+1 DAY)""",(subscription_fee,))

    trainingfeeslist = cur.fetchall()

    total_revenue = subfeeslist[0][1] + trainingfeeslist[0][1] + get_retail_sales()

    return render_template('admin_financial_report.html',
                           subfeeslist=subfeeslist,
                           trainingfeeslist=trainingfeeslist,
                           total_revenue=total_revenue,
                           #today_date=datetime.now().date().replace(day=1) - timedelta(days=1)
						   )


# trainer classes
@app.route("/trainer/view_classes")
def trainer_classes():

    class_id = request.args.get("class_id")
    class_type = request.args.get("class_type")

    cur = getCursor()
    cur.execute("""
        SELECT
            CM.classname,
            DATE(C.startdatetime) as startdate,
            TIME(C.startdatetime) as starttime,
            R.roomname,
            R.capacity,
            R.capacity - (SELECT COUNT(enrollmentid) FROM enrollment E WHERE E.classid = C.classid) AS spacesleft,
            UM.userid AS traineeid,
            CONCAT(UM.firstname, ' ', UM.familyname) AS trainee
        FROM class C
        LEFT JOIN enrollment E ON E.classid = C.classid
        JOIN classmaster CM ON CM.classmasterid = C.classmasterid
        LEFT JOIN user UM ON UM.userid = E.memberid
        JOIN room R ON R.roomid = C.roomid
        WHERE C.classid = %s """, (class_id,))
    
    class_details = cur.fetchall()

    class_detail = None

    if (len(class_details) > 0):
        class_detail = class_details[0]
        classes = class_details

    return render_template("trainer_classes.html", class_detail=class_detail, classes=classes, class_type=class_type)


# get user details by user id
def get_user_by_user_id(userid):
    cur = getCursor()
    cur.execute("""SELECT 
                    u.userid, 
                    u.username, 
                    ut.usertypename,
                    u.firstname, 
                    u.familyname, 
                    u.dateofbirth, 
                    u.housenumbername, 
                    u.street, 
                    u.town, 
                    u.city, 
                    u.postalcode, 
                    u.isactive 
		FROM user u JOIN usertype ut ON u.usertypeid = ut.usertypeid WHERE userid = %s;""", (userid,))

    select_result = cur.fetchall()

    return select_result


# get the subscription status for a given member
# then set the status in a global variable
# so that we can use it in throughout the app
def set_subscription_status(memberid):
    cur = getCursor()
    cur.execute(
        """SELECT COUNT(*) FROM 
        subscription 
        WHERE memberid = %s 
        AND enddate >= CURDATE();""", (memberid,))
    subscription_result = cur.fetchall()

    if (len(subscription_result) > 0):
        global has_active_subscription
        has_active_subscription = subscription_result[0][0] > 0

# get subscription fee
def get_subscription_fee():

    # dummy data for now
    # to indicate subscription fee for the membership
    subscription_fee = 100

    return subscription_fee


# get retail sales
def get_retail_sales():

    # dummy data for now
    # to indicate retail sales income for the month    
    retail_sales = 100

    return retail_sales


# get future classes for a trainer
def get_classes_for_trainer(trainer_id, class_type):
    
        cur = getCursor()
        cur.execute("""
            SELECT 
                C.classid,
                CM.classname,
                CM.classtype,
                R.roomname,
                DATE(C.startdatetime),
                TIME(C.startdatetime)
            FROM class C
            JOIN user UT ON UT.userid = C.trainerid
            JOIN classmaster CM ON CM.classmasterid = C.classmasterid
            JOIN room R ON R.roomid = C.roomid
            WHERE C.trainerid = %s
            AND CM.classtype = %s
            AND C.startdatetime >= NOW()
            ORDER BY C.startdatetime;""", (trainer_id, class_type,))
        classes = cur.fetchall()

        if(len(classes) == 0):
            classes = None
    
        return classes


# injects the values into all the templates,
# so we can handle menu items in the layout according to the user login status
# i.e. logged in user details throught the app
@app.context_processor
def injectStore():

    username = logged_in_username
    user_type = logged_in_user_type

    return dict(
        username=username,
        user_type=user_type
    )


