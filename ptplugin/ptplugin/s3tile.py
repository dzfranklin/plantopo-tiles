import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mapproxy.client.http import HTTPClient
from mapproxy.config.loader import TileSourceConfiguration
from mapproxy.config.spec import mapproxy_yaml_spec
from mapproxy.util.ext.dictspec.spec import combined


class S3TileSourceConfiguration(TileSourceConfiguration):
    source_type = ("s3tile",)

    spec_source_def = combined(
        list(mapproxy_yaml_spec["sources"].values())[0].specs["tile"],
        dict(s3={"profile_name": str()}),
    )

    def http_client(self, url):
        s3_conf = self.conf.get("s3", {})
        return S3HTTPClient(s3_conf), url


class S3HTTPClient(HTTPClient):
    def __init__(self, s3_conf):
        super().__init__()

        profile_name = s3_conf.get("profile_name")

        sess = boto3.Session(profile_name=profile_name)
        creds = sess.get_credentials().get_frozen_credentials()
        region_name = sess.region_name

        self.sigv4 = SigV4Auth(creds, "s3", region_name)

    def open(self, url, data=None, method=None, headers=None):
        method = method or "GET"
        if method not in ("GET", "HEAD"):
            raise NotImplementedError(
                "S3HTTPClient: Only GET and HEAD methods are supported"
            )
        if data is not None:
            raise NotImplementedError("S3HTTPClient: Data payloads are not supported")

        req = AWSRequest(
            method=method,
            url=url,
            headers=headers,
        )
        self.sigv4.add_auth(req)
        prepped = req.prepare()
        return super().open(
            prepped.url,
            method=prepped.method,
            headers=dict(prepped.headers),
        )
