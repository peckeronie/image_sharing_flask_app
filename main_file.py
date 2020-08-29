from flask import Flask, render_template, request, redirect, Blueprint
from flask_paginate import Pagination, get_page_parameter, get_page_args
from werkzeug.utils import secure_filename
import sqlite3
app = Flask(__name__)
example_db = "testimageweb.db"
ALLOWED_EXTENSIONS = ['jfif', 'png', 'jpg', 'jpeg', 'gif']

def verify_user_info(username):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    username_check = c.execute('''SELECT * from users_table WHERE username = ?;''',(username,)).fetchone()
    if username_check != None:
        return False
    else:
        return True

    conn.commit()
    conn.close()

def check_username_password(username,password_hash):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    db_password = c.execute('''SELECT hash_password from users_table WHERE username = ?;''',(username,)).fetchone()
    if db_password[0] == None:
        return False
    elif(int(db_password[0]) == password_hash):
        return True
    else:
        return False
    conn.commit()
    conn.close()

def insert_new_user_into_database(username, password_hash):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    bookmark_table_name = "Bookmark_" + str(username)
    c.execute('''INSERT into users_table VALUES (?,?,?);''',(username,password_hash,bookmark_table_name))
    conn.commit()
    conn.close()

def get_tags_and_count():
    tag_dict = {}
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    all_tags = c.execute('''SELECT DISTINCT tag from tags_table;''').fetchall()
    for tag in all_tags:
        count = c.execute('''SELECT COUNT(image_id) from tags_table WHERE tag = ? LIMIT 10;''',(tag[0],)).fetchone()
        tag_dict[tag] = count[0]
    return tag_dict
    conn.commit()
    conn.close()

def get_images(offset=0, per_page=10):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    all_images = c.execute('''SELECT * from images_table;''').fetchall()
    return all_images[offset: offset + per_page]
    conn.commit()
    conn.close()

def generate_sql_query(tags_count, page_num):
    #construct a query after the user has searched for tags
    query_str = ""
    where_str = ""
    for count in range(1,tags_count+1):
        if(count == 1):
            query_str += "SELECT t1.image_id FROM table as t1"
            where_str += "WHERE t1.tag = ?"
        else:
            query_str += " INNER JOIN table as t" + str(count) + " ON t1.image_id = t" + str(count) + ".image_id"
            where_str += " and t" + str(count) + ".tag = ?"
    where_str += " ORDER BY t1.image_id DESC LIMIT 10 OFFSET " + str(page_num*10-10) + ";"
    return query_str + where_str

# when a user bookmarks an image, store their bookmarks in a separate table
def save_bookmark(username, img_id):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    bookmark_table_name = "Bookmark_" + str(username)
    #table_name = c.execute('''SELECT bookmark_table_id from users_table WHERE username = ?;''',(username,)).fetchone()
    c.execute('''CREATE TABLE IF NOT EXISTS ''' + bookmark_table_name + ''' (bookmark_id int);''')
    c.execute('''INSERT into ''' + bookmark_table_name + ''' VALUES (?);''', (img_id,))
    conn.commit()
    conn.close()

def delete_bookmark(username, img_id):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    bookmark_table_name = "Bookmark_" + str(username)
    #table_name = c.execute('''SELECT bookmark_table_id from users_table WHERE username = ?;''',(username,)).fetchone()
    c.execute('''CREATE TABLE IF NOT EXISTS ''' + bookmark_table_name + ''' (bookmark_id int);''')
    c.execute('''DELETE FROM ''' + bookmark_table_name + ''' WHERE bookmark_id = ?;''', (img_id,))
    conn.commit()
    conn.close()

# upload an image into the database
def insert_into_database(image_source, image_tags):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    latest_image_id = c.execute('''SELECT id from images_table ORDER BY id DESC;''').fetchone()
    if latest_image_id == None:
        latest_image_id = 0
    else:
        latest_image_id = latest_image_id[0] + 1

    c.execute('''INSERT into images_table VALUES (?,?);''',(latest_image_id,image_source))
    for tag in image_tags:
        c.execute('''INSERT into tags_table VALUES (?,?);''',(latest_image_id,tag))
    conn.commit()
    conn.close()
    print("Insert into database completed")

def allowed_file(filename):
    if "." in filename:
        if filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            return True
    return False

@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        if request.files:
            uploaded_image = request.files["image"]
            uploaded_tags = request.form["image_tags"]
            input_list = uploaded_tags.split()
            if uploaded_image.filename == '':
                return redirect(request.url)
            if uploaded_image and allowed_file(uploaded_image.filename):
                filename = secure_filename(uploaded_image.filename)
                insert_into_database(filename, input_list)

@app.route('/', methods=["GET", "POST"]) # '/' is default webpage
def login_default():
    if request.method == "POST":
        for key, val in request.form.items():
            if val == "":
                return render_template("login_page.html",message="Please enter values for both fields.")
        username_input = request.form["username"]
        password_hash = request.form["password"].__hash__()
        check_valid_user = check_username_password(username_input,password_hash)
        if check_valid_user:
            return redirect(url_for('home_page',username=username_input))
        else:
            return render_template("login_page.html",message="Username or password not valid. Please try again.")
    return render_template("login_page.html")

@app.route('/sign_up_page', methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        for key, val in request.form.items():
            if val == "":
                return render_template("signup_page.html",message="Please enter values for both fields.")
        username_input = request.form["username"]
        password_hash = request.form["password"].__hash__()
        check_valid_username = verify_user_info(username_input)
        if check_valid_username:
            insert_new_user_into_database(username_input,password_hash)
            return redirect(url_for('home_page',username=username_input))
        else:
            return render_template("signup_page.html",message="Username already taken. Please enter a different username.")
    return render_template("signup_page.html")

# page that shows search results
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == "POST":
        input = request.form["Search"]
        if input != "":
            return redirect(url_for('load_results', query=input))

# main webpage that the user sees after logging in
@app.route('/home',methods=['GET', 'POST'])
def home_page(username):
    #display up to 10 images on every page
    page = 1
    per_page = 10
    offset = (page - 1) * per_page
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    all_images = c.execute('''SELECT * from images_table;''').fetchall()
    page_images = get_images(offset,per_page)
    pagination = Pagination(page=page, per_page=per_page, total=len(all_images), record_name='Images')
    current_tag_dict = get_tags_and_count()

    return render_template('index.html',imgs=page_images,pagination=pagination, tag_bar=current_tag_dict)
    conn.commit()
    conn.close()
    #return render_template('view.html',posts=posts)

@app.route('/image/<imageurl>')
def show_single_image(imageurl, imageid, username):
    return render_template('image_page.html', img_src=imageurl, img_id=imageid, verified_user=username)

@app.route('/bookmark/<id>', methods=['GET', 'POST'])
def bookmark(user, id):
    if request.method == "POST":
        if request.form['submit'] == 'Submit':
            save_bookmark(user, id)

@app.route('/results/<query>', methods=['GET', 'POST'])
def load_results(query):
    #after the user has searched for tags, output 10 search results per page
    search_image_urls = []
    search_tags_list = query.split()
    if(len(search_tags_list) == 1):
        tags_tuple = (search_tags_list[0],)
    else:
        tags_tuple = tuple(search_tags_list)
    tags_num = len(search_tags_list)
    query = generate_sql_query(tags_num)

    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    search_image_ids = c.execute(query,tags_tuple).fetchall()

    #     search_image_ids = c.execute('''SELECT t1.image_id
    # FROM table as t1
    # INNER JOIN table as t2 ON t1.image_id= t2.image_id
    # INNER JOIN table as t3 ON t1.image_id= t3.image_id
    # WHERE t1.tag = ? and t2.tag = ? and t3.tag = ?
    # ORDER BY t1.image_id DESC
    # LIMIT 100;''',(search_tags_list[0],search_tags_list[1],search_tags_list[2])).fetchall()
    if (len(search_results) != 0):
        for id in search_image_ids:
            image_url = c.execute('''SELECT * from images_table WHERE id = ?;''',(id[0],)).fetchone()
            search_image_urls.append(image_url)

    return render_template("search_results_template.html",imgs=search_image_urls)
    conn.commit()
    conn.close()

# @app.route('/home', methods=['GET', 'POST'])
# def home_page(username):
#
#     conn = sqlite3.connect(example_db)
#     c = conn.cursor()
#     all_images = c.execute('''SELECT * from images_table;''').fetchall()
#     images_per_page = 10
#     number_of_pages = int(len(all_images)/images_per_page) + (len(all_images) % images_per_page > 0) #round up
#     current_tag_dict = get_tags_and_count()
#
#     return render_template("website_home_page.html",page_count=number_of_pages, tag_bar=current_tag_dict)

# @app.route('/page/<count>')
# def display_images(count):
#
#     #display 10 images on every page, first page shows most recent images in home page
#     conn = sqlite3.connect(example_db)
#     c = conn.cursor()
#     #img_list = []
#     all_images = c.execute('''SELECT * from images_table;''').fetchall()
#     images_per_page = 10
#     img_list = [all_images[i * images_per_page:(i + 1) * images_per_page] for i in range((len(all_images) + images_per_page - 1) // images_per_page)]
#
#     return render_template("image_page_template.html",imgs=img_list[count-1])
