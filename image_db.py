#create the database

import sqlite3
import datetime
import time
import schedule
import requests
import os
from bs4 import BeautifulSoup
example_db = "testimageweb.db"

# users_table:
# username: a string
# hash_password: hash value of the user's entered password
# bookmark_table_name: the name of another table that holds the user's bookmarked image id's (ints)

# tags_table:
# image_id: a number corresponding to an image
# tag: a string tag for the image (ex: food, cake)

# images_table:
# id: a number corresponding to an image
# image: the image path associated with this id (from the computer)

def create_database():
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    #c.execute('''CREATE TABLE IF NOT EXISTS id_table (id int, date text, type text, category text);''')
    c.execute('''CREATE TABLE IF NOT EXISTS users_table (username text, hash_password int, bookmark_table_name text);''')
    c.execute('''CREATE TABLE IF NOT EXISTS tags_table (image_id int, tag text);''')
    c.execute('''CREATE TABLE IF NOT EXISTS images_table (id int, image text);''')
    conn.commit() # commit commands
    conn.close() # close connection to database

#upload an image into the database
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

def request_handler(request):
    conn = sqlite3.connect(example_db)
    c = conn.cursor()
    #when a user signs up
    if(request['method'] == 'POST' and request['values']['query'] == 'Sign_up'):
        username = request["values"]["username"]
        username_check = c.execute('''SELECT * from users_table WHERE username = ?;''',(username,)).fetchone()
        if username_check != None:
            return "Username already taken. Please enter a different username."
        else:
            password_hash = request["values"]["password"]
            bookmark_table_name = "Bookmark_" + str(username)
            c.execute('''INSERT into users_table VALUES (?,?,?);''',(username,password_hash,bookmark_table_name))
    #when a user bookmarks an image, store their bookmarks in a separate table
    elif(request['method'] == 'POST' and request['values']['query'] == 'Bookmark'):
        username = request["values"]["username"]
        bookmarked_image = request["values"]["bookmark_image_id"]
        #bookmark_table_name = "Bookmark_" + str(username)
        table_name = c.execute('''SELECT bookmark_table_name from users_table WHERE username = ?;''',(username,)).fetchone()
        c.execute('''CREATE TABLE IF NOT EXISTS ''' + table_name[0] + ''' (bookmark_id int);''')
        c.execute('''INSERT into ''' + bookmark_table_name + ''' VALUES (?);''', (bookmarked_image,))
        conn.commit()
        conn.close()

# link: url for the picture (from a website)
# folder: name of folder that will store all images
def save_image_locally(link, folder):
    file_name = link.split("/")[-1]
    image_request = requests.get(link)
    if (os.path.isdir(folder) == False): #make folder to hold wallpaper images
        os.mkdir(folder)
    file_path = os.path.join(folder, file_name)
    print(file_path)
    open(file_path, 'wb').write(image_request.content) #save the image into the folder
    image_request.close()
    print("image saved")
    abs_path = os.path.abspath(file_path)
    insert_into_database(abs_path,tags_list)

##def lookup_database(): #for testing
##    conn = sqlite3.connect(example_db)
##    c = conn.cursor()
##    things = c.execute('''SELECT * FROM id_table ORDER BY date DESC;''').fetchall()
##    for row in things:
##        print(row)
##    print("Category table completed")
##    apps = c.execute('''SELECT * FROM app_table ORDER BY info_id DESC;''').fetchall()
##    for x in apps:
##        print(x)
##    conn.commit()
##    conn.close()
##    print("Lookup completed")
