# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2020 KuraLabs S.R.L
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Application entry point module.
"""

from pathlib import Path
from os.path import extsep
from json import dumps, loads
from logging import getLogger
from datetime import datetime

from setproctitle import setproctitle

from .scrapper import scrappe_data
from .utils import is_url, download, unzip
from .readers import DistrictsReader, VotersReader
from .render import list_renderers, render, render_scrapped


log = getLogger(__name__)


def main(args):
    """
    Application main function.

    :param args: An arguments namespace.
    :type args: :py:class:`argparse.Namespace`

    :return: Exit code.
    :rtype: int
    """
    setproctitle('tse2sql')

    start = datetime.now()
    log.debug('Start timestamp: {}'.format(start.isoformat()))

    # Download archive if required
    archive = args.archive
    if is_url(archive):
        archive = download(archive, subdir='tse2sql')

    # Calculate digest and unzip archive
    extracted = unzip(archive)
    filename = Path(archive).stem

    # Parse distelec file
    distelec = DistrictsReader(extracted)
    distelec.parse()

    # Save analysis file
    analysis = dumps(distelec.analyse(), sort_keys=True, indent=4)
    log.info('Distelec analysis:\n{}'.format(analysis))
    with open('{}.data.json'.format(filename), 'w') as fd:
        fd.write(analysis)

    # Open voters file
    voters = VotersReader(extracted, distelec)
    voters.open()

    # Get list of renderers to use
    if args.renderer is None:
        renderers = list_renderers()
    else:
        renderers = [args.renderer]

    # Build rendering payload
    payload = {
        'provinces': distelec.provinces,
        'cantons': distelec.cantons,
        'districts': distelec.districts,
        'voters': voters
    }

    # Generate SQL output
    for rdr in renderers:
        print('Writing output for {} ...'.format(rdr))
        with open('{}.{}.sql'.format(filename, rdr), 'w') as sqlfile:
            render(payload, rdr, sqlfile)

    # Write samples files
    with open('{}.samples.json'.format(filename), 'w') as samplesfile:
        samplesfile.write(dumps(voters.samples, indent=4))

    # Log elapsed time
    end = datetime.now()
    print('Elapsed time: {}s'.format((end - start).seconds))

    return 0


def main_scrapper(args):
    """
    Scrapper main function.

    :param args: An arguments namespace.
    :type args: :py:class:`argparse.Namespace`

    :return: Exit code.
    :rtype: int
    """
    setproctitle('tse2sql-scrapper')

    start = datetime.now()
    log.info('Start timestamp: {}'.format(start.isoformat()))

    # Get list of renderers to use
    if args.renderer is None:
        renderers = list_renderers()
    else:
        renderers = [args.renderer]

    # Grab user data
    # XXX: This ugly line is required, Python (as of 3.7) doesn't have a way to
    #      obtain the true stem of a filename by removing all suffixes.
    filename, _ = Path(args.samples).stem.split(extsep, 1)
    with open(args.samples) as fd:
        samples = loads(fd.read())

    # Execute data scrapper
    scrapped_data, unscrapped_data = scrappe_data(samples)

    # Generate SQL output
    for rdr in renderers:
        print('Writing output for {} ...'.format(rdr))
        with open('{}.scrapped.{}.sql'.format(filename, rdr), 'w') as sqlfile:
            render_scrapped(scrapped_data, rdr, sqlfile)

    # Generate JSON output of unscrapped data
    with open(
            '{}.unscrapped.json'.format(filename),
            mode='wt', encoding='utf-8'
    ) as unscrappedfd:
        unscrappedfd.write(
            dumps(unscrapped_data, indent=4, ensure_ascii=False)
        )

    # Log elapsed time
    end = datetime.now()
    print('Elapsed time: {}s'.format((end - start).seconds))

    return 0


__all__ = ['main', 'main_scrapper']
