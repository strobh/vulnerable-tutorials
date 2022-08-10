The objective is to prevent an attacker who has gained access to the stored password hashes from being able to crack them (i.e., to find out the corresponding passwords).

To prevent the efficient calculation of password hashes (brute-force attack), you should only use **hash functions designed for hashing passwords, such as **PBKDF2, bcrypt, or argon2**. The calculation of these hash algorithms requires a certain amount of computational effort, which **slows down the calculation considerably** (e.g., to only 5 password hashes per second) and makes it harder to try billions of passwords:

<pre class="language-java line-numbers"><code>
// REGISTRATION: when the user creates an account
// ------------

// password entered by the user
String password = "...";

// generate salt
SecureRandom random = new SecureRandom();
byte[] salt = new byte[16];
random.nextBytes(salt);

// hash the password using PBKDF2 algorithm and store it in the database
KeySpec spec = new PBEKeySpec(password.toCharArray(), salt, 65536, 24 * 8);
SecretKeyFactory f = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
byte[] hash = f.generateSecret(spec).getEncoded();
Base64.Encoder encoder = Base64.getEncoder();
String pw_salt = enc.encodeToString(salt);
String pw_hash = enc.encodeToString(hash);



// LOGIN: when the user logs in
// ------------

// password entered by the user
String password = "...";

// load password hash from the database
String pw_hash = load_pw_from_database();
String pw_salt = load_salt_from_database();
byte[] hash = Base64.getUrlDecoder().decode(pw_hash);
byte[] salt = Base64.getUrlDecoder().decode(pw_salt);

// calculate the hash of the password
KeySpec spec = new PBEKeySpec(password.toCharArray(), salt, 65536, 24 * 8);
SecretKeyFactory f = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
byte[] check_hash = f.generateSecret(spec).getEncoded();

// verify that the correct password was entered
int zero = 0;
for (int idx = 0; idx < check_hash.length; ++idx) {
    zero |= hash[salt.length + idx] ^ check_hash[idx];
}

if (zero == 0) {
    System.out.println("correct password");
}
else {
    System.out.println("incorrect password");
}
</code></pre>

To prevent that all users who have the same password also have the same password hash, the code snippet above **generates a random string** (called `salt`) using `random.nextBytes()`. This salt is **hashed together with the password** and is different for each user.

Example: Password hashes with salt (using the `bcrypt` hash function)

```
password123 + ddsYzDfKAH4F9fOYVh9Mve  --->  AVAlfghXiTW59Vbt74cpS.AMn.i5rte
password123 + 0Vl2RYbcb764tDaf44M2lO  --->  6aSZIA0a7mTrKunoYkAXEH/CGNKBbMa
```

The same password (`password123`), but with different salts (`ddsYzDfKAH4F9fOYVh9Mve` and `0Vl2RYbcb764tDaf44M2lO`), results in different hashes. The advantage is that an attacker can no longer try to calculate hashes for all users at the same time. Instead, the attacker has to try passwords for each salt (and thus each user) individually. For example, `password123+saltA` and `test123+saltA` for user A and `password123+saltB` and `test123+saltB` for user B. This **slows down the attacker even more and makes it practically impossible to find out the passwords for all users**.

*Note*: The salt must be stored in the database for each user to be able to calculate the hash again later (e.g. when the user logs in).
