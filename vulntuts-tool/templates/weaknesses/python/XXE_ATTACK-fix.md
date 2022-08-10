The vulnerability can be fixed by configuring the XML parser such that it **does not resolve external entities**.

This can be achieved by one of the following ways:

- If DOCTYPE is not necessary, completely disable all DOCTYPE declarations.
- If external entities are not necessary, completely disable their declarations.
- If external entities are necessary then:
    - Use XML processor features, if available, to authorize only required protocols (eg: https).
    - And use an entity resolver (and optionally an XML Catalog) to resolve only trusted entities.

To configure the XML parsers named in the previous section accordingly (see [SonarRules](https://rules.sonarsource.com/python/RSPEC-2755) for the source of this fix):

<pre class="language-python line-numbers"><code>
parser = etree.XMLParser(resolve_entities=False, no_network=True)
</code></pre>
