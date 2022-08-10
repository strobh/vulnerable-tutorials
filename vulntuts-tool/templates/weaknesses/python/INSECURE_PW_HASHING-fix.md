The objective is to prevent an attacker who has gained access to the stored password hashes from being able to crack them (i.e., to find out the corresponding passwords).

To prevent the efficient calculation of password hashes (brute-force attack), you should only use **hash functions designed for hashing passwords, such as bcrypt or argon2**. The calculation of these hash algorithms requires a certain amount of computational effort, which **slows down the calculation considerably** (e.g., to only 5 password hashes per second) and makes it harder to try billions of passwords:

<pre class="language-python line-numbers"><code>
# REGISTRATION: when the user creates an account
# ------------

# password entered by the user
password = "..."

# hash the password using bcrypt algorithm and store it in the database
pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())



# LOGIN: when the user logs in
# ------------

# password entered by the user
password = "..."

# load password hash from the database
pw_hash = load_pw_from_database()

# verify that the correct password was entered
if bcrypt.checkpw(password, pw_hash):
    print("correct password")
else:
    print("incorrect password")
</code></pre>

To prevent that all users who have the same password also have the same password hash, the code snippet above **generates a random string** (called `salt`) using `bcrypt.gensalt()`. This salt is **hashed together with the password** and is different for each user.

Example: Password hashes with salt (using the `bcrypt` hash function)

```
password123 + ddsYzDfKAH4F9fOYVh9Mve  --->  AVAlfghXiTW59Vbt74cpS.AMn.i5rte
password123 + 0Vl2RYbcb764tDaf44M2lO  --->  6aSZIA0a7mTrKunoYkAXEH/CGNKBbMa
```

The same password (`password123`), but with different salts (`ddsYzDfKAH4F9fOYVh9Mve` and `0Vl2RYbcb764tDaf44M2lO`), results in different hashes. The advantage is that an attacker can no longer try to calculate hashes for all users at the same time. Instead, the attacker has to try passwords for each salt (and thus each user) individually. For example, `password123+saltA` and `test123+saltA` for user A and `password123+saltB` and `test123+saltB` for user B. This **slows down the attacker even more and makes it practically impossible to find out the passwords for all users**.

*Note*: The salt must be stored in the database for each user to be able to calculate the hash again later (e.g. when the user logs in). If you use `bcrypt.hashpw()` the salt is included in the password hash and you do not have to store it manually.
