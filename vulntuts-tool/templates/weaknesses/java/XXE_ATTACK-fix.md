The vulnerability can be fixed by configuring the XML parser such that it **does not resolve external entities**.

This can be achieved by one of the following ways:

- If DOCTYPE is not necessary, completely disable all DOCTYPE declarations.
- If external entities are not necessary, completely disable their declarations.
- If external entities are necessary then:
    - Use XML processor features, if available, to authorize only required protocols (eg: https).
    - And use an entity resolver (and optionally an XML Catalog) to resolve only trusted entities.

To configure the XML parsers named in the previous section accordingly (see [SonarRules](https://rules.sonarsource.com/java/RSPEC-2755) for the source of this fix):

<pre class="language-java line-numbers"><code>
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
// to be compliant, completely disable DOCTYPE declaration:
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
// or completely disable external entities declarations:
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
// or prohibit the use of all protocols by external entities:
factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
// or disable entity expansion but keep in mind that this doesn't prevent fetching external entities
// and this solution is not correct for OpenJDK < 13 due to a bug: https://bugs.openjdk.java.net/browse/JDK-8206132
factory.setExpandEntityReferences(false);

SAXParserFactory factory = SAXParserFactory.newInstance();
// to be compliant, completely disable DOCTYPE declaration:
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
// or completely disable external entities declarations:
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
// or prohibit the use of all protocols by external entities:
SAXParser parser = factory.newSAXParser();
parser.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
parser.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

XMLInputFactory factory = XMLInputFactory.newInstance();
// to be compliant, completely disable DOCTYPE declaration:
factory.setProperty(XMLInputFactory.SUPPORT_DTD, false);
// or completely disable external entities declarations:
factory.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, Boolean.FALSE);
// or prohibit the use of all protocols by external entities:
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

TransformerFactory factory = javax.xml.transform.TransformerFactory.newInstance();
// to be compliant, prohibit the use of all protocols by external entities:
factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_STYLESHEET, "");

SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
// to be compliant, completely disable DOCTYPE declaration:
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
// or prohibit the use of all protocols by external entities:
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

SAXReader xmlReader = new SAXReader();
xmlReader.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);

SAXBuilder builder = new SAXBuilder();
builder.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
builder.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
</code></pre>
