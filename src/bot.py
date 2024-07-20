#! /usr/bin/env python3

print("Starting bagelbot...")


import os
import sys
from bagelshop.logging import log


log.info("STARTING. =============================")
log.debug(sys.version.strip("\n"))
log.debug(sys.version_info)
log.debug(f"Program args: {sys.argv}")
log.debug(f"CWD: {os.getcwd()}")


import bot_common
import argparse
import asyncio


async def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()
    await bot_common.deploy_with_config(args)


if __name__ == "__main__":
    asyncio.run(main())
