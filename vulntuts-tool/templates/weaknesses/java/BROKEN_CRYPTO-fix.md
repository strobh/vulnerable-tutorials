General consensus is that you should never [roll your own cryptography](https://security.stackexchange.com/a/18198), instead you should rely on known algorithms that have been analyzed by hundreds of experts.
Also, you should never implement the algorithms yourself, but use well-tested libraries, since it is very easy to make mistakes when implementing cryptographic algorithms.

The following overview offers only a selection of secure algorithms and can cover only a small part of potential usage scenarios.

#### Encryption algorithms

It is recommended to use a high-level cryptography library instead of using low-level functions. This already relieves the developer of many sources of errors, since most libraries have secure default settings.
Ideally you should, for example, not need to generate encryption keys or random nonces/IVs yourself, as critical mistakes can already be made at this stage.

There is a broad consensus to use only encryption algorithms that provide message integrity and authenticity. That means, the receiver can confirm that the message came from the stated sender (its authenticity) and has not been changed (integrity). Examples are `AES` encryption in `GCM` mode or `RSA` encryption with `OAEP` padding.

The most recommended and well-tested library is [Bouncy Castle](https://www.bouncycastle.org/documentation.html).

Example: Using the pyca/cryptography library to encrypt and decrypt a message

<pre class="language-java line-numbers"><code>
import java.security.Security
import org.bouncycastle.jcajce.provider.BouncyCastleFipsProvider

public class Demo {
    public void static main(String args[])
    {
        Security.addProvider(new BouncyCastleFipsProvider());

        // message to encrypt
        byte[] message = byte[10];

        SecretKey secKey = generateKey();
        Object[] gcmOutput = gcmEncrypt(secKey, message);

        AlgorithmParameters gcmParameters = (AlgorithmParameters)gcmOutput[0];
        byte[] ciphertext = (byte[])gcmOutput[1];

        byte[] plaintext = gcmDecrypt(secKey, gcmParameters, ciphertext);
    }

    public static SecretKey generateKey()
        throws GeneralSecurityException
    {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES", "BCFIPS");
        keyGenerator.init(256);
        return keyGenerator.generateKey();
    }

    public static Object[] gcmEncrypt(SecretKey key, byte[] data)
        throws GeneralSecurityException
    {
        final byte[] gcmNonceByte = new byte[12];
        SecureRandom secureRandomGcm = new SecureRandom();
        secureRandomGcm.nextBytes(gcmNonceByte);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding", "BCFIPS");
        cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, gcmNonceByte));
        return new Object[] { cipher.getParameters(), cipher.doFinal(data), };
    }

    public static byte[] gcmDecrypt(SecretKey key, AlgorithmParameters gcmParameters, byte[] cipherText)
        throws GeneralSecurityException
    {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding", "BCFIPS");
        cipher.init(Cipher.DECRYPT_MODE, key, gcmParameters);
        return cipher.doFinal(cipherText);
    }
}
</code></pre>

#### Hash/Message digest algorithms

The most commonly used cryptographic hash function is `SHA-256`.

A typical use of hash functions is to perform validation checks, i.e., checking whether changes have been made to an object.
If you want to hash passwords instead, you should use special hash algorithms that have been designed exactly for this use case such as `bcrypt` or `argon2`.
