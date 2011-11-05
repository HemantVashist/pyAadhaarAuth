#!/usr/bin/env python
#
#Copyright (C) 2011 by Venkata Pingali (pingali@gmail.com) & TCS 
#(for only the modifications; main copyright held by Valos)
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.
#
#
#
# $Id: sign3.py 363 2006-01-01 18:03:07Z valos $
#
# PyXMLSec example: Signing a file with a dynamicaly created template and
# an X509 certificate.
#
# Signs a file using a dynamicaly created template, key from PEM file and
# an X509 certificate. The signature has one reference with one enveloped 
# transform to sign the whole document except the <dsig:Signature/> node 
# itself. The key certificate is written in the <dsig:X509Data/> node.
#
# This example was developed and tested with OpenSSL crypto library. The 
# certificates management policies for another crypto library may break it.
#
# Usage: 
#	./sign3.py <xml-doc> <pkcs12-file> <password>
#
# Example:
#	./sign3.py sign3-doc.xml public.p12 hello > sign3-res.xml
#
# The result signature could be validated using verify3 example:
#	./verify3.py sign3-res.xml rootcert.pem
#
# This is free software; see COPYING file in the source
# distribution for preciese wording.
# 
# Copyright (C) 2003-2004 Valery Febvre <vfebvre@easter-eggs.com>
#


#
# signature 
#
# usage: 
#       python signature.py <xmlfile> 
# 
#       The xml file can contain the signature template or not. 
#       The code can handle both situations. Right now does
#       not have a way to verify the result. 
#
#

import os, sys
import libxml2
import xmlsec
from config import Config 
from M2Crypto import RSA, BIO, Rand, m2, EVP, X509

__author__ = "Venkata Pingali"
__copyright__ = "Copyright 2011,Venkata Pingali and TCS (for derived parts only)" 
__credits__ = ["UIDAI", "MindTree", "GeoDesic", "Viral Shah"] 
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Venkata Pingali"
__email__ = "pingali@gmail.com"
__status__ = "Pre-release"


class AuthRequestSignature(): 
    
    def __init__(self, use_template=False): 
        self.dsig_ctx = None
        self._init_xmlsec = False 
        self._use_template = use_template
        return 
        
    def init_xmlsec(self): 

        # Init libxml library
        libxml2.initParser()
        libxml2.substituteEntitiesDefault(1)
        
        # Init xmlsec library
        if xmlsec.init() < 0:
            print "Error: xmlsec initialization failed."
            # XXX This should do something else...
            return sys.exit(-1)
        
        # Check loaded library version
        if xmlsec.checkVersion() != 1:
            print "Error: loaded xmlsec library version is not compatible.\n"
            sys.exit(-1)

        # Init crypto library
        if xmlsec.cryptoAppInit(None) < 0:
            print "Error: crypto initialization failed."
            
        # Init xmlsec-crypto library
        if xmlsec.cryptoInit() < 0:
            print "Error: xmlsec-crypto initialization failed."

        self._init_xmlsec = True 

    def shutdown_xmlsec(self):
        
        if not self._init_xmlsec:
            return 

        # Shutdown xmlsec-crypto library
        xmlsec.cryptoShutdown()

        # Shutdown crypto library
        xmlsec.cryptoAppShutdown()

        # Shutdown xmlsec library
        xmlsec.shutdown()

        # Shutdown LibXML2
        libxml2.cleanupParser()


    # Signs the xml_file using private key from pkcs_file and dynamicaly
    # created enveloped signature template. The certificate from cert_file
    # is placed in the <dsig:X509Data/> node.
    # Returns 0 on success or a negative value if an error occurs.
    def sign_file(self, xml_file, signed_xml_file, pkcs_file, password):
        assert(xml_file)
        assert(pkcs_file)
        assert(password)
        
        # Load template
        if not self.check_filename(xml_file):
            return -1
        
        doc = libxml2.parseFile(xml_file)
        if doc is None or doc.getRootElement() is None:
            print "Error: unable to parse file \"%s\"" % xml_file
            return self.cleanup(doc)
        
        
        if self._use_template: 
            # If the template is already in the text ready to be filled 
            signNode = xmlsec.findNode(doc.getRootElement(),
                                       xmlsec.NodeSignature, 
                                       xmlsec.DSigNs);
            if signNode is None:
                print "Error: failed to find signature template"
                return self.cleanup(doc)
                
        else:
            # If the signature structure has to be constructed and added.
            
            # Create signature template for RSA-SHA1 enveloped signature
            signNode = xmlsec.TmplSignature(doc, xmlsec.transformExclC14NId(),
                                            xmlsec.transformRsaSha1Id(), None)
            
            # Add <dsig:Signature/> node to the doc
            doc.getRootElement().addChild(signNode)
            
            # Add reference
            refNode = signNode.addReference(xmlsec.transformSha1Id(),
                                            None, None, None)
            if refNode is None:
                print "Error: failed to add reference to signature template"
                return self.cleanup(doc)
            
            # Add enveloped transform
            if refNode.addTransform(xmlsec.transformEnvelopedId()) is None:
                print "Error: failed to add enveloped transform to reference"
                return self.cleanup(doc)
        
            # Add <dsig:KeyInfo/> and <dsig:X509Data/>
            keyInfoNode = signNode.ensureKeyInfo(None)
            if keyInfoNode is None:
                print "Error: failed to add key info"
                return self.cleanup(doc)
            
            x509DataNode = keyInfoNode.addX509Data() 
            if x509DataNode is None:
                print "Error: failed to add X509Data node"
                return self.cleanup(doc)

            # Sample code from here.
            # http://ndg-security.ceda.ac.uk/browser/TI12-security/trunk/python/NDG/XMLSecDoc.py?rev=920
            if xmlsec.addChild(x509DataNode,
                               xmlsec.NodeX509Certificate) is None:
                print "Error: failed to X509certificate to x509DataNode" 
                return self.cleanup(doc)
	
            if xmlsec.addChild(x509DataNode,
                               xmlsec.NodeX509SubjectName) is None:
                print "Error: failed to X509SubjectName to x509DataNode" 
                return self.cleanup(doc)

        # endif (if use_template..) 
    
        # Create signature context, we don't need keys manager in this
        # example
        dsig_ctx = xmlsec.DSigCtx()
        if dsig_ctx is None:
            print "Error: failed to create signature context"
            return self.cleanup(doc)
        
        # Store the context..
        self.dsig_ctx = dsig_ctx 

        # Load private key, assuming that there is not password
        if not self.check_filename(pkcs_file):
            return self.cleanup(doc, dsig_ctx)
        
        #key = xmlsec.cryptoAppKeyLoad(key_file, xmlsec.KeyDataFormatPem,
        #                              None, None, None)
        key = xmlsec.cryptoAppPkcs12Load(pkcs_file, password, None, None)
        if key is None:
            print "Error: failed to load private pem key from \"%s\"" % pkcs_file
            return self.cleanup(doc, dsig_ctx)

        dsig_ctx.signKey = key
        
        # Load certificate and add to the key
        # if not check_filename(cert_file):
        #    return self.cleanup(doc, dsig_ctx)
        # if xmlsec.cryptoAppKeyCertLoad(key, cert_file, xmlsec.KeyDataFormatPem) < 0:
        #    print "Error: failed to load pem certificate \"%s\"" % cert_file
        #    return self.cleanup(doc, dsig_ctx)
        
        # Set key name to the file name, this is just an example!
        if key.setName(pkcs_file) < 0:
            print "Error: failed to set key name for key from \"%s\"" % pkcs_file
            return self.cleanup(doc, dsig_ctx)
        
        # Sign the template
        if dsig_ctx.sign(signNode) < 0:
            print "Error: signature failed"
            return self.cleanup(doc, dsig_ctx)
        
        # Print signed document to stdout
        #doc.dump("-")
        #doc.formatDump("-", 0)
        import libxml2mod
        
        fp = file(signed_xml_file, "w")
        libxml2mod.xmlDocFormatDump(fp, doc._o, 0)
        fp.close()
        
        print "Please check output file ", signed_xml_file
        
        # Success
        return self.cleanup(doc, dsig_ctx, 1)

    #=> From verify1
    # Verifies XML signature in xml_file using public key from key_file.
    # Returns 0 on success or a negative value if an error occurs.
    def verify_file(self, xml_file, key_file):
        assert(xml_file)
        assert(key_file)

        # Load XML file
        if not self.check_filename(xml_file):
            return -1

        doc = libxml2.parseFile(xml_file)
        if doc is None or doc.getRootElement() is None:
            print "Error: unable to parse file \"%s\"" % tmpl_file
            return self.cleanup(doc)

        # Find start node
        node = xmlsec.findNode(doc.getRootElement(),
                               xmlsec.NodeSignature, xmlsec.DSigNs)

        # Create signature context, we don't need keys manager in this example
        dsig_ctx = xmlsec.DSigCtx()
        if dsig_ctx is None:
            print "Error: failed to create signature context"
            return self.cleanup(doc)

        # Load private key, assuming that there is not password
        key = xmlsec.cryptoAppKeyLoad(key_file, xmlsec.KeyDataFormatPem,
                                      None, None, None)
        if key is None:
            print "Error: failed to load private pem key from \"%s\"" % key_file
            return self.cleanup(doc, dsig_ctx)

        dsig_ctx.signKey = key

        # Set key name to the file name, this is just an example!
        if not self.check_filename(key_file):
            return self.cleanup(doc, dsig_ctx)

        if key.setName(key_file) < 0:
            print "Error: failed to set key name for key from \"%s\"" % key_file
            return self.cleanup(doc, dsig_ctx)

        # Verify signature
        if dsig_ctx.verify(node) < 0:
            print "Error: signature verify"
            return self.cleanup(doc, dsig_ctx)

        # Print verification result to stdout
        if dsig_ctx.status == xmlsec.DSigStatusSucceeded:
            print "Signature is OK"
        else:
            print "Signature is INVALID"

        # Success
        return self.cleanup(doc, dsig_ctx, 1)
    
    def cleanup(self, doc=None, dsig_ctx=None, res=-1):
        if dsig_ctx is not None:
            dsig_ctx.destroy()
            if doc is not None:
                doc.freeDoc()
        return res
            

    def check_filename(self, filename):
        if os.access(filename, os.R_OK):
            return 1
        else:
            print "Error: XML file \"%s\" not found OR no read access" % filename
            return 0

if __name__ == "__main__":
    assert(sys.argv)
    if len(sys.argv) < 2:
        print """
Error: command line should specify a config file.

Usage: signature.py <config-file>

$ cat example.cfg
# Sign a given XML using the pkcs 
common: { 
    pkcs_path: 'fixtures/public.p12',
    pkcs_password: 'public',
    private_key: 'fixtures/public_key.pem',
....
}
sign: {
    command: 'sign'
    xml: 'fixtures/authrequest.xml',
    signedxml: 'fixtures/authrequest.xml.sig',
}
$ cat example2.cfg 
# Verify the signature in a signed xml
sign: {
    command: 'verify'
    signedxml: 'fixtures/authrequest.xml.sig',
}
"""

    #=> Read the configuration. 
    # XXX Document the format of the configuration file
    cfg = Config(sys.argv[1])
    
    if cfg.sign.command == "sign": 

        # Sign the XML file 
        # XXX Should probably move the init_xmlsec into sign_file itself
        sign = AuthRequestSignature() 
        sign.init_xmlsec() 
        res = sign.sign_file(cfg.sign.xml,
                             cfg.sign.signedxml,
                             cfg.common.pkcs_path,
                             cfg.common.pkcs_password)
        sign.shutdown_xmlsec() 
    
        print "Please check the output in %s " % signed_xml_file 
    elif cfg.sign.command == "verify": 

        # Load this or another file for verification using the 
        # private key of public.12 
        verify = AuthRequestSignature()
        verify.init_xmlsec() 
        res = verify.verify_file(cfg.sign.signedxml, 
                                 cfg.common.private_key)
        verify.shutdown_xmlsec() 
    else:
        raise Exception("Unknown error") 
    
    sys.exit(res)