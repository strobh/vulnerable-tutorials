Instead of hard-coded credentials, the application could have a "first login" mode where no credentials are required. When logging in for the first time, the **user is required to enter a strong password that is stored on the system**.

The password should be hashed with a cryptographic hash function and stored in a database or a configuration file. A cryptographic hash function is an algorithm that maps data (e.g., a password) to fixed-size values (called "hash"). It is a one-way function. That means it is **not possible to invert or reverse** the computation: Given a password you can easily calculate the hash, but you cannot calculate the password if you only know the hash of it.

```
Password  --->  Hash
Hash      -/->  Password (not possible)
```

Example: Password hashes (using the insecure `md5` hash function)

```
password123   --->  482c811da5d5b4bc6d497ffa98491e38
password1234  --->  bdc87b9c894da5168059e00ebffb9077
```

An attacker looking for the password to a hash has no choice but to use a **brute-force attack** to crack the password hashes. The attacker generates billions of possible passwords, calculates the hashes of them, and hopes that he finds the correct hash (and thus the corresponding password). That is why it is very important that the hash function is not too easy to compute. If the software uses a fast hash function (such as `md5` or `sha256`) for the passwords, the hashes can be calculated very efficiently: Modern GPUs can calculate more than a million hashes per second. So an attacker can try through many passwords very quickly and may be able to **find a password for the corresponding hash after only a few seconds**.

This is simplified by the fact that many users have bad passwords that can be found in lists of common passwords (e.g., from previous password breaches on other platforms). Thus, an attacker first calculates the hashes of known passwords in his brute-force attack. These bad passwords are, therefore, cracked very quickly.

For this reason, you should only use **hash functions designed for hashing passwords, such as bcrypt or argon2**. The calculation of these hash algorithms requires a certain amount of computational effort, which **slows down the calculation considerably** (e.g., to only 5 password hashes per second) and makes it harder to try billions of passwords:

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

The next problem is that all users who have the same password also have the same password hash. If an attacker finds the password to a hash, he **knows the password for all users with this password hash**.

To prevent this, the code snippet above **generates a random string** (called `salt`) using `random.nextBytes()` **that is hashed together with the password** and that is different for each user.

Example: Password hashes with salt (using the `bcrypt` hash function)

```
password123 + ddsYzDfKAH4F9fOYVh9Mve  --->  AVAlfghXiTW59Vbt74cpS.AMn.i5rte
password123 + 0Vl2RYbcb764tDaf44M2lO  --->  6aSZIA0a7mTrKunoYkAXEH/CGNKBbMa
```

The same password (`password123`), but with different salts (`ddsYzDfKAH4F9fOYVh9Mve` and `0Vl2RYbcb764tDaf44M2lO`), results in different hashes. The advantage is that an attacker can no longer try to calculate hashes for all users at the same time. Instead, the attacker has to try passwords for each salt (and thus each user) individually. For example, `password123+saltA` and `test123+saltA` for user A and `password123+saltB` and `test123+saltB` for user B. This **slows down the attacker even more and makes it practically impossible to find out the passwords for all users**.

*Note*: The salt must be stored in the database for each user to be able to calculate the hash again later (e.g. when the user logs in).
