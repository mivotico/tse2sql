# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Carlos Jenkins
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

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from json import dumps
from logging import getLogger

from .utils import is_url, download, sha256, unzip
from .readers import DistrictsReader, VotersReader
from .render import list_templates, render


log = getLogger(__name__)


def main(args):
    """
    Application main function.

    :param args: An arguments namespace.
    :type args: :py:class:`argparse.Namespace`
    :return: Exit code.
    :rtype: int
    """
    # Download archive if required
    archive = args.archive
    if is_url(archive):
        archive = download(archive, subdir='tse2sql')

    # Calculate digest and unzip archive
    digest = sha256(archive)
    extracted = unzip(archive)

    # Parse distelec file
    distelec = DistrictsReader(extracted)
    distelec.parse()

    # Save analysis file
    analysis = dumps(distelec.analyse(), sort_keys=True, indent=4)
    log.info('Distelec analysis:\n{}'.format(analysis))
    with open('{}.data.json'.format(digest), 'w') as fd:
        fd.write(analysis)

    # Open voters file
    voters = VotersReader(extracted, distelec)
    voters.open()

    # Get list of templates to render
    if args.template is None:
        templates = list_templates()
    else:
        templates = [args.template]

    # Build rendering payload
    payload = {
        'extracted': extracted,
        'digest': digest,
        'provinces': distelec.provinces,
        'cantons': distelec.cantons,
        'districts': distelec.districts,
        'voters': voters
    }

    # Generate SQL output
    for tpl in templates:
        log.info('Writing template {} ...'.format(tpl))
        with open('{}.{}.sql'.format(digest, tpl), 'w') as sql_output:
            sql_output.write(render(tpl, payload))

    return 0


__all__ = ['main']
