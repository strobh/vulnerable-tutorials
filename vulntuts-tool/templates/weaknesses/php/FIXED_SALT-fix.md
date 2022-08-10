The objective is to prevent an attacker who has gained access to the stored password hashes from being able to crack them (i.e., to find out the corresponding passwords).

<pre class="language-php line-numbers"><code>
// REGISTRATION: when the user creates an account
// ------------

// password entered by the user
$password = $_POST["password"];

// hash the password using bcrypt algorithm and store it in the database
$pw_hash = password_hash($password, PASSWORD_DEFAULT);



// LOGIN: when the user logs in
// ------------

// password entered by the user
$password = $_POST["password"];

// load password hash from the database
$pw_hash = load_pw_from_database();

// verify that the correct password was entered
if (password_verify($password, $pw_hash)) {
    echo "correct password";
}
else {
    echo "incorrect password"
}
</code></pre>

To prevent that all users who have the same password also have the same password hash, the code snippet above **generates a random string** (called `salt`) in `password_hash()`. **This salt is hashed together with the password and is different for each user**.

Example: Password hashes with salt (using the `bcrypt` hash function)

```
password123 + ddsYzDfKAH4F9fOYVh9Mve  --->  AVAlfghXiTW59Vbt74cpS.AMn.i5rte
password123 + 0Vl2RYbcb764tDaf44M2lO  --->  6aSZIA0a7mTrKunoYkAXEH/CGNKBbMa
```

The same password (`password123`), but with different salts (`ddsYzDfKAH4F9fOYVh9Mve` and `0Vl2RYbcb764tDaf44M2lO`), results in different hashes. The advantage is that an attacker can no longer try to calculate hashes for all users at the same time. Instead, the attacker has to try passwords for each salt (and thus each user) individually. For example, `password123 + ddsYzDfKAH4F9fOYVh9Mve` and `test123 + ddsYzDfKAH4F9fOYVh9Mve` for user A and `password123 + 0Vl2RYbcb764tDaf44M2lO` and `test123 + 0Vl2RYbcb764tDaf44M2lO` for user B. This **slows down the attacker and makes it practically impossible to find out the passwords for all users**.

*Note*: The salt must be stored in the database for each user to be able to calculate the hash again later (e.g. when the user logs in). If you use `password_hash()` the salt is included in the password hash and you do not have to store it manually.
