The most secure and modern approach is to use **prepared statements**.

<pre class="language-python line-numbers" data-line="17-19"><code>
import mysql.connector

# connect to database
connection = mysql.connector.connect(
    host='localhost',
    database='db_name',
    user='db_user',
    password='db_password'
)
cursor = connection.cursor(prepared=True)

# username and password entered by the user
username = "foo"
password = "bar"

# username and password are supplied separately to the prepared statement
query = "SELECT * FROM users WHERE name = %s AND password = %s"
params = (username, password)
cursor.execute(query, params)
result = cursor.fetchone()

if result == None:
    print("wrong username or password")
else:
    print("successfully logged in")

cursor.close()
connection.close()
</code></pre>

Prepared statements make a strict distinction between the query and the data to be used in the query. In the query, `%s` marks where the data should be inserted later. Afterwards, we supply the values as second parameter (as tuple) to the method `cursor.execute()`. The database takes care that the data is always interpreted as data only. Manipulation of the query is thus no longer possible.
