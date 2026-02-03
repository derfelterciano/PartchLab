#!/usr/bin/env python3
"""
This programs retrieves the experimental summaries given
a signals UUID

WARNING: REQUIRES THE FOLLOWING PACKAGES:

pip install tqdm urllib3

"""

import requests
from requests.auth import HTTPBasicAuth
from requests import Response
import argparse
import json
import os
import getpass
from urllib.parse import urljoin
from time import sleep
import logging
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

# NOTE: you  may need to pip install urllib3 and tqdm

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
BASE_URL = "https://csc-signals.pbsci.ucsc.edu"
API_VERSION = 1.1


def get_response(
    url: str, auth: HTTPBasicAuth, verify: bool = False, stream: bool = False
) -> Response:
    """
    Sends a request to the API. We wrap this to make our code look cleaner

    Args:
        url (str): API URL
        auth (HTTPBasicAuth): Basic authenticatiom
        verify (bool, optional): verifies requests. Defaults to False.
        stream (bool, optional): streams request calls useful for downloading
            files. Defaults to False.

    Returns:
        Response: Response body
    """
    return requests.get(url=url, auth=auth, verify=verify, stream=stream)


def get_auth_validation(version: float, auth: HTTPBasicAuth) -> int:
    """
    Authenticates user's credentials

    Args:
        version (float): api version (typically 1.1)
        auth (HTTPBasicAuth): _description_

    Returns:
        int: status code for response
    """
    get_link = f"/api/{version}/authentication/validate"

    with get_response(urljoin(BASE_URL, get_link), auth=auth) as resp:
        return resp.status_code


def get_download_link(
    uuid: str,
    auth: HTTPBasicAuth,
    raw_cell_data: bool = False,
    verify: bool = False,
    attemps: int = 3,
) -> str:
    """
    Grabs the appropriate download links from the signals summary response.

    Args:
        uuid (str): dataset uuid
        auth (HTTPBasicAuth): basic http authentication
        raw_cell_data (bool, optional): Retrieves raw cell data link.
            Defaults to False.
        verify (bool, optional): Verifies api request. Defaults to False.
        attemps (int, optional): _description_. Defaults to 3.

    Returns:
        str: _description_
    """
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

                    if not raw_cell_data:
                        results_download = json_data["results"][0]["download"]
                        # print(json.dumps(json_data, indent=2))
                    else:
                        # below is for retrieving raw cell data
                        results_download = json_data["results"][0]

                        if not results_download["celldata"]:
                            logging.error(f"No cell data found for: {uuid}")
                            logging.warning(f"Retrying query!")
                            sleep(1)
                            continue

                        results_download = results_download["download_cell_data"][0][
                            "download"
                        ]

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


class CommandLine:
    def __init__(self, in_opts=None):
        self.parser = argparse.ArgumentParser(
            description="Downloads Signals data",
            prog="signals_summaries.py",
            add_help=True,
            prefix_chars="-",
        )

        self.parser.add_argument(
            "-i",
            "--uuid",
            action="store",
            required=True,
            nargs="?",
            type=str,
            help="Signals UUID input",
        )

        self.parser.add_argument(
            "-o",
            "--output",
            action="store",
            required=True,
            nargs="?",
            type=str,
            help="Specifies the file path where tsv file will be place (not file name)",
        )

        self.parser.add_argument(
            "-c",
            "--celldata",
            action="store_true",
            default=False,
            required=False,
            help="Retrieves raw cell data instead",
        )

        self.parser.add_argument(
            "-u",
            "--user",
            action="store",
            required=True,
            help="Signals username",
            nargs="?",
            type=str,
        )

        self.parser.add_argument(
            "-p",
            "--password",
            action="store",
            required=False,
            help="Signals password (will prompt if not provided, or set SIGNALS_PASSWORD env var)",
            nargs="?",
            type=str,
        )

        self.parser.add_argument(
            "--chunksize",
            action="store",
            required=False,
            nargs="?",
            type=int,
            default=102400,
            help="chunksize for writing tsv file (def: 102400)",
        ),
        self.parser.add_argument(
            "--attempts",
            action="store",
            required=False,
            default=3,
            type=int,
            help="Number of connection re-attemps (def: 3)",
        )

        curr_args = in_opts if in_opts is not None else None
        self.args = self.parser.parse_args(curr_args)

        # Password parsing
        if not self.args.password:
            self.args.password = os.getenv("SIGNALS_PASSWORD")
            if not self.args.password:
                self.args.password = getpass.getpass("Signals password: ")


def main(in_opts=None):
    cl = CommandLine(in_opts)

    user = cl.args.user
    password = cl.args.password
    uuid = cl.args.uuid
    output = cl.args.output
    raw_cell_data = cl.args.celldata
    chunksize = cl.args.chunksize
    attempts = cl.args.attempts

    basic_auth = HTTPBasicAuth(username=user, password=password)

    if get_auth_validation(API_VERSION, auth=basic_auth) != 200:
        logging.error("Could not verify login credentials!")
        exit(1)

    logging.info("Successfully connected to signals!")

    link = get_download_link(
        uuid=uuid, auth=basic_auth, raw_cell_data=raw_cell_data, attemps=attempts
    )

    out_name_type = "cellByCell_data" if raw_cell_data else "wellSummaries"
    out_name = f"{uuid}_{out_name_type}.tsv"
    out_name = os.path.join(output, out_name)

    _ = save_file(
        download_link=link, outName=out_name, auth=basic_auth, chunksize=chunksize
    )

    # user = "pipeline"
    # password = "qdKlEDYXLt5q44eId"
    # test_uuid = "51059402-990a-11f0-a062-02420a00010d"
    # basic_auth = HTTPBasicAuth(username=user, password=password)

    # code = get_auth_validation(1.1, basic_auth)
    # print(code)

    # link = get_download_link(uuid=test_uuid, auth=basic_auth)
    # print(link)

    # save_file(link, outName="test.tsv", auth=basic_auth, chunksize=524288000)


if __name__ == "__main__":
    main()
