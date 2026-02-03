#!/usr/bin/env python3
"""
This programs retrieves the experimental summaries given
a signals UUID
"""

import requests
from requests.auth import HTTPBasicAuth
from requests import Response
import json
import os
import sys
from urllib.parse import urljoin
from time import sleep
import logging
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

# NOTE: you  may need to pip install urllib3 and tqdm

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
BASE_URL = "https://csc-signals.pbsci.ucsc.edu"


def get_response(
    url: str, auth: HTTPBasicAuth, verify: bool = False, stream: bool = False
) -> Response:
    return requests.get(url=url, auth=auth, verify=verify, stream=stream)


def get_auth_validation(version: float, auth: HTTPBasicAuth) -> int:
    get_link = f"/api/{version}/authentication/validate"

    with get_response(urljoin(BASE_URL, get_link), auth=auth) as resp:
        return resp.status_code


def get_download_link(
    uuid: str, auth: HTTPBasicAuth, verify: bool = False, attemps: int = 3
) -> str:
    for _ in range(attemps):
        try:
            datasetURL = urljoin(BASE_URL, f"/api/1.1/data/dataset/{uuid}")
            with get_response(url=datasetURL, auth=auth, verify=verify) as dataset_resp:

                if dataset_resp.status_code != 200:
                    logging.error(f"CODE: {dataset_resp.status_code} for UUID: {uuid}")
                    logging.warning("Retrying Query!")
                    sleep(1)
                    continue
                else:
                    json_data = dataset_resp.json()
                    results_download = json_data["results"][0]["download"]
                    # print(json.dumps(json_data, indent=2))

                    # below is for retrieving raw cell data
                    # results_download = json_data["results"][0]
                    # results_download = results_download["download_cell_data"][0][
                    #     "download"
                    # ]

                    logging.info(f"Found download for {uuid}")
                    return results_download

        except Exception as e:
            logging.error(f"<get_download_link> : {type(e)}: {e}")
            logging.warning("Retrying connection")
            sleep(1)


def save_file(
    download_link: str,
    outName: str,
    auth: HTTPBasicAuth,
    chunksize: int = 8192,
    verify: bool = False,
    attempts: int = 3,
):
    for _ in range(attempts):
        try:
            link = urljoin(BASE_URL, download_link)
            with get_response(
                url=link, auth=auth, verify=verify, stream=True
            ) as response:

                if response.status_code != 200:
                    logging.error(
                        f"CODE: {response.status_code} for link: {download_link}"
                    )
                    logging.warning("Retrying Query!")
                    sleep(1)
                    continue
                else:
                    total_size = int(response.headers.get("content-length", 0))
                    logging.info(f"Downloading: {download_link}")

                    with open(outName, "wb") as f:
                        with tqdm(
                            total=total_size, unit="B", unit_scale=True, desc=outName
                        ) as pbar:
                            for chunk in response.iter_content(chunk_size=chunksize):
                                f.write(chunk)
                                pbar.update(len(chunk))
                return response.status_code
        except Exception as e:
            logging.error(f"<save_file> {type(e)}: {e}")
            logging.warning("Retrying download!\n")
            sleep(1)


def main():
    user = "pipeline"
    password = "qdKlEDYXLt5q44eId"
    test_uuid = "51059402-990a-11f0-a062-02420a00010d"
    basic_auth = HTTPBasicAuth(username=user, password=password)

    code = get_auth_validation(1.1, basic_auth)
    print(code)

    link = get_download_link(uuid=test_uuid, auth=basic_auth)
    print(link)

    save_file(link, outName="test.tsv", auth=basic_auth, chunksize=524288000)


if __name__ == "__main__":
    main()
