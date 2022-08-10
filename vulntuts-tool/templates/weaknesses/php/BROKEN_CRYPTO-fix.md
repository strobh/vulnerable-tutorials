General consensus is that you should never [roll your own cryptography](https://security.stackexchange.com/a/18198), instead you should rely on known algorithms that have been analyzed by hundreds of experts.
Also, you should never implement the algorithms yourself, but use well-tested libraries, since it is very easy to make mistakes when implementing cryptographic algorithms.

The following overview offers only a selection of secure algorithms and can cover only a small part of potential usage scenarios.

#### Encryption algorithms

It is recommended to use a high-level cryptography library instead of using low-level functions. This already relieves the developer of many sources of errors, since most libraries have secure default settings.
Ideally you should, for example, not need to generate encryption keys or random nonces/IVs yourself, as critical mistakes can already be made at this stage.

There is a broad consensus to use only encryption algorithms that provide message integrity and authenticity. That means, the receiver can confirm that the message came from the stated sender (its authenticity) and has not been changed (integrity). Examples are `AES` encryption in `GCM` mode or `RSA` encryption with `OAEP` padding.

Often recommended and well-tested libraries are

- [openssl](https://www.php.net/manual/en/book.openssl.php),
- [sodium](https://www.php.net/manual/en/book.sodium.php),
- or [php-encryption](https://github.com/defuse/php-encryption).

Example: Using the php-encryption library to encrypt and decrypt a message

<pre class="language-php line-numbers"><code>
use Defuse\Crypto\Crypto;
use Defuse\Crypto\Key;

// do this once then store it somewhere secret
$key = Key::createNewRandomKey();

$message = "A really secret message.";

// encrypt the message
$ciphertext = Crypto::encrypt($message, $key);

// decrypt the message
$plaintext = Crypto::decrypt($ciphertext, $key);
</code></pre>

Example: Using the openssl library to encrypt and decrypt a message

<pre class="language-php line-numbers"><code>
$key = random_bytes(32);
$message = "A really secret message.";

// encrypt the message
$encrypted = encrypt($key, $message);

// decrypt the message
$decrypted = decrypt($key, $encrypted);

public function encrypt($key, $data)
{
    $tag_length = 16;
    $cipher = 'aes-256-gcm';
    $iv_len = openssl_cipher_iv_length($cipher);

    $iv = random_bytes($iv_len);
    $tag = ""; // will be filled by openssl_encrypt

    $ciphertext = openssl_encrypt(
        $data,
        $cipher,
        $key,
        OPENSSL_RAW_DATA,
        $iv,
        $tag,
        "",
        $tag_length
    );

    return base64_encode($iv . $ciphertext . $tag);
}

public function decrypt($key, $data)
{
    $tag_length = 16;
    $cipher = 'aes-256-gcm';
    $iv_len = openssl_cipher_iv_length($cipher);

    $data = base64_decode($data);

    $iv = substr($data, 0, $iv_len);
    $ciphertext = substr($data, $iv_len, -$tag_length);
    $tag = substr($data, -$tag_length);

    return openssl_decrypt(
        $ciphertext,
        $cipher,
        $key,
        OPENSSL_RAW_DATA,
        $iv,
        $tag
    );
}
</code></pre>

#### Hash/Message digest algorithms

The most commonly used cryptographic hash function is `SHA-256`.

A typical use of hash functions is to perform validation checks, i.e., checking whether changes have been made to an object.
If you want to hash passwords instead, you should use special hash algorithms that have been designed exactly for this use case such as `bcrypt` or `argon2`.
