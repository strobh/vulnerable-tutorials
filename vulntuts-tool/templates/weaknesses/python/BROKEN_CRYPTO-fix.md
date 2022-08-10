General consensus is that you should never [roll your own cryptography](https://security.stackexchange.com/a/18198), instead you should rely on known algorithms that have been analyzed by hundreds of experts.
Also, you should never implement the algorithms yourself, but use well-tested libraries, since it is very easy to make mistakes when implementing cryptographic algorithms.

The following overview offers only a selection of secure algorithms and can cover only a small part of potential usage scenarios.

#### Encryption algorithms

It is recommended to use a high-level cryptography library instead of using low-level functions. This already relieves the developer of many sources of errors, since most libraries have secure default settings.
Ideally you should, for example, not need to generate encryption keys or random nonces/IVs yourself, as critical mistakes can already be made at this stage.

There is a broad consensus to use only encryption algorithms that provide message integrity and authenticity. That means, the receiver can confirm that the message came from the stated sender (its authenticity) and has not been changed (integrity). Examples are `AES` encryption in `GCM` mode or `RSA` encryption with `OAEP` padding.

Often recommended and well-tested libraries are

- [pyca/cryptography](https://cryptography.io/en/latest/),
- [PyCryptodome](https://www.pycryptodome.org/en/latest/src/introduction.html),
- and [PyNaCl](https://pynacl.readthedocs.io/en/latest/).

Example: Using the pyca/cryptography library to encrypt and decrypt a message

<pre class="language-python line-numbers"><code>
from cryptography.fernet import Fernet

# this key must be kept secret
key = Fernet.generate_key()

f = Fernet(key)

# encrypt a message
encrypted = f.encrypt(b"A really secret message.")

# decrypt the message again
plaintext = f.decrypt(encrypted)
</code></pre>

Example: Using the PyNaCl library to encrypt and decrypt a message

<pre class="language-python line-numbers"><code>
import nacl.secret
import nacl.utils

# this must be kept secret
key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

box = nacl.secret.SecretBox(key)

# encrypt a message
encrypted = box.encrypt(b"A really secret message.")

# decrypt the message again
plaintext = box.decrypt(encrypted)
</code></pre>

#### Hash/Message digest algorithms

The most commonly used cryptographic hash function is `SHA-256`.

A typical use of hash functions is to perform validation checks, i.e., checking whether changes have been made to an object.
If you want to hash passwords instead, you should use special hash algorithms that have been designed exactly for this use case such as `bcrypt` or `argon2`.
