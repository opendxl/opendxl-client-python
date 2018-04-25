# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

"""
Helpers for crypto operations used by the cli tools - e.g., for creating
certificate requests and private keys
"""

from __future__ import absolute_import
import logging

from asn1crypto import x509, pem, csr
from oscrypto import asymmetric

from dxlclient import DxlUtils

logger = logging.getLogger(__name__)


def _bytes_to_unicode(obj):
    """
    Convert a non-`bytes` type object into a unicode string.

    :param obj: the object to convert
    :return: If the supplied `obj` is of type `bytes`, decode it into a unicode
        string. If the `obj` is anything else (including None), the original
        `obj` is returned. If the object is converted into a unicode string,
        the type would be `unicode` for Python 2.x or `str` for Python 3.x.
    """
    return obj.decode() if isinstance(obj, bytes) else obj


class X509Name(object):
    """
    Holder for an X.509 distinguished name, e.g., /C=US/CN=myname.
    """
    def __init__(self, common_name):
        """
        Constructor parameters:

        :param str common_name: Common Name (CN) attribute
        """
        self._common_name = common_name
        self._country_name = None
        self._state_or_province_name = None
        self._locality_name = None
        self._organization_name = None
        self._organizational_unit_name = None
        self._email_address = None

    @property
    def common_name(self):
        """
        Common Name (CN) attribute

        :rtype: str
        """
        return self._common_name

    @property
    def country_name(self):
        """
        Country (C) attribute

        :rtype: str
        """
        return self._country_name

    @country_name.setter
    def country_name(self, value):
        """
        Country (C) attribute to set

        :param str value: new name
        """
        self._country_name = value

    @property
    def state_or_province_name(self):
        """
        State or Province (ST) attribute

        :rtype: str
        """
        return self._state_or_province_name

    @state_or_province_name.setter
    def state_or_province_name(self, value):
        """
        State or Province (ST) attribute to set

        :param str value: new name
        """
        self._state_or_province_name = value

    @property
    def locality_name(self):
        """
        Locality (C) attribute

        :rtype: str
        """
        return self._locality_name

    @locality_name.setter
    def locality_name(self, value):
        """
        Locality (L) attribute to set

        :param str value: new name
        """
        self._locality_name = value

    @property
    def organization_name(self):
        """
        Organization (O) attribute

        :rtype: str
        """
        return self._organization_name

    @organization_name.setter
    def organization_name(self, value):
        """
         Organization (O) attribute to set

         :param str value: new name
         """
        self._organization_name = value

    @property
    def organizational_unit_name(self):
        """
        Organizational Unit (OU) attribute

        :rtype: str
        """
        return self._organizational_unit_name

    @organizational_unit_name.setter
    def organizational_unit_name(self, value):
        """
         Organizational Unit (OU) attribute to set

         :param str value: new name
         """
        self._organizational_unit_name = value

    @property
    def email_address(self):
        """
        e-mail address attribute

        :rtype: str
        """
        return self._email_address

    @email_address.setter
    def email_address(self, value):
        """
         e-mail address attribute to set

         :param str value: new name
         """
        self._email_address = value


_CRYPTO_SIGN_DIGEST = "sha256"
_CRYPTO_KEY_TYPE = "rsa"
_CRYPTO_KEY_BITS = 2048


class _KeyPair(object):
    """
    RSA public / private key pair generator
    """
    def __init__(self):
        self._key_pair = asymmetric.generate_pair(_CRYPTO_KEY_TYPE,
                                                  _CRYPTO_KEY_BITS)
        self._public_key, self._private_key = self._key_pair

    @property
    def private_key(self):
        """
        The private key

        :rtype: asymmetric.PrivateKey
        """
        return self._private_key

    @property
    def public_key(self):
        """
        The public key

        :rtype: asymmetric.PublicKey
        """
        return self._public_key

    def private_key_as_pem(self, passphrase=None):
        """
        Return the private key as a PEM-encoded string.

        :param passphrase: If a `str` object is supplied, encrypt the private
            key with the passphrase before converting it to PEM format. If
            `None` is supplied, convert it to PEM format without performing any
            encryption.
        :return: private key in PEM format
        :rtype: str
        """
        return asymmetric.dump_private_key(self._private_key,
                                           _bytes_to_unicode(passphrase))


class _CertificateRequest(object):
    """
    Certificate request generator
    """
    def __init__(self, subject, key_pair, sans=None):
        """
        Constructor parameters:

        :param X509Name subject: subject to add to the certificate request
        :param _KeyPair key_pair: key pair containing the public key to use
            when creating the signature for the certificate request
        :param sans: collection of dns names to insert into a subjAltName
            extension for the certificate request
        :type sans: list(str) or tuple(str) or set(str)
        """
        csr_info = self._csr_info(subject, key_pair.public_key, sans)
        csr_signature = asymmetric.rsa_pkcs1v15_sign(
            key_pair.private_key,
            csr_info.dump(),
            _CRYPTO_SIGN_DIGEST
        )
        self._req = csr.CertificationRequest({
            "certification_request_info": csr_info,
            "signature_algorithm": {
                "algorithm": u"{}_rsa".format(_CRYPTO_SIGN_DIGEST)
            },
            "signature": csr_signature})

    def _csr_info(self, subject, public_key, sans):
        """
        Create the csr info portion of the certificate request"s ASN.1
        structure

        :param X509Name subject: subject to add to the certificate request
        :param asymmetric.PublicKey public_key: public key to use when creating
            the certificate request"s signature
        :param sans: collection of dns names to insert into a subjAltName
            extension for the certificate request
        :type sans: None or list(str) or tuple(str) or set(str)
        :return: the certificate request info structure
        :rtype: csr.CertificationRequestInfo
        """
        x509_subject = x509.Name.build(self._subject_as_dict(subject))
        extensions = [(u"basic_constraints",
                       x509.BasicConstraints({"ca": False}),
                       False),
                      (u"key_usage",
                       x509.KeyUsage({"digital_signature",
                                      "key_encipherment"}),
                       True),
                      (u"extended_key_usage",
                       x509.ExtKeyUsageSyntax([u"client_auth"]),
                       False)]
        if sans:
            names = x509.GeneralNames()
            for san in sans:
                names.append(x509.GeneralName("dns_name",
                                              _bytes_to_unicode(san)))
            extensions.append((u"subject_alt_name", names, False))

        return csr.CertificationRequestInfo({
            "version": u"v1",
            "subject": x509_subject,
            "subject_pk_info": public_key.asn1,
            "attributes":
                [{"type": u"extension_request",
                  "values": [[self._create_extension(x) for x in extensions]]}]})

    @staticmethod
    def _create_extension(extension):
        """
        Create an ASN.1 certificate request extension structure

        :param tuple extension: tuple with three values: name of the
            extension (str), value for the extension(str), and whether or not
            the extension should be considered critical (bool)
        :return: the extension
        :rtype: dict
        """
        name, value, critical = extension
        return {"extn_id": name,
                "extn_value": value,
                "critical": critical}

    @staticmethod
    def _set_subject_dict_kvp(subject, subject_dict, name):
        """
        Obtain the value from the subject for the `name` attribute. Set the
        corresponding key / value pair into the `subject_dict`.

        :param subject: object containing the attribute value to retrieve
        :param subject_dict: dictionary to insert the retrieved attribute info
            into
        :param name: name of the attribute in the `subject` and corresponding
            key in the `subject_dict`
        """
        value = getattr(subject, name)
        if value is not None:
            subject_dict[name] = _bytes_to_unicode(value)

    def _subject_as_dict(self, subject):
        """
        Convert the supplied subject from a :class:`X509Name` into a `dict`.

        :param X509Name subject: subject to convert
        :return: `dict` containing info from the `subject`
        :rtype: dict(str, str)
        """
        subject_dict = {}
        for attribute in [u"common_name",
                          u"country_name",
                          u"state_or_province_name",
                          u"locality_name",
                          u"organization_name",
                          u"organizational_unit_name",
                          u"email_address"]:
            self._set_subject_dict_kvp(subject, subject_dict, attribute)
        return subject_dict

    def dump_to_pem(self):
        """
        Dump the certificate request to a PEM-encoded string

        :return: the certificate request PEM string
        :rtype: str
        """
        return pem.armor(u"CERTIFICATE REQUEST", self._req.dump())


class CsrAndPrivateKeyGenerator(object):
    """
    Certificate request and private key generator
    """
    def __init__(self, subject, sans=None):
        """
        Constructor parameters:

        :param X509Name subject: subject to add to the certificate request
        :param sans: collection of dns names to insert into a subjAltName
            extension for the certificate request
        :type sans: list(str) or tuple(str) or set(str)
        """
        self._key_pair = _KeyPair()
        self._csr = _CertificateRequest(subject, self._key_pair, sans)

    def save_csr_and_private_key(self, csr_filename, private_key_filename,
                                 passphrase=None):
        """
        Save the certificate request and private key to disk in PEM format

        :param csr_filename: filename of the certificate request
        :param private_key_filename: filename of the private key
        :param passphrase: If a `str` object is supplied, encrypt the private
            key with the passphrase before converting it to PEM format. If
            `None` is supplied, convert it to PEM format without performing any
            encryption.
        """
        logger.info("Saving csr file to %s", csr_filename)
        DxlUtils.save_to_file(csr_filename, self._csr.dump_to_pem())
        logger.info("Saving private key file to %s", private_key_filename)
        DxlUtils.save_to_file(private_key_filename,
                              self._key_pair.private_key_as_pem(passphrase),
                              0o600)

    @property
    def csr(self):
        """
        Return the certificate request as PEM-encoded string

        :return: the PEM-encoded certificate request
        ​:rtype: str
        """
        return self._csr.dump_to_pem()


def validate_cert_pem(pem_text, message_on_exception=None):
    """
    Validate that the supplied `pem_text` string contains a PEM-encoded
    certificate

    :param str pem_text: text to validate as a PEM-encoded certificate
    :param str message_on_exception: extra text to add into an exception if
        a validation failure occurs
    :raise Exception: if the `pem_text` does not represent a valid PEM-encoded
        certificate
    """
    try:
        pem_bytes = pem_text if isinstance(pem_text, bytes) \
            else pem_text.encode()
        object_name, _, der_bytes = pem.unarmor(pem_bytes)
        if object_name != "CERTIFICATE":
            raise Exception(
                "Expected CERTIFICATE type for PEM, Received: {}".format(
                    object_name))
        x509.Certificate.load(der_bytes)
    except Exception as ex:
        logger.error("%s. Reason: %s",
                     message_on_exception or
                     "Failed to validate certificate PEM",
                     ex)
        logger.debug("Certificate PEM: %s", pem_text)
        raise
