# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
from shutil import copyfile
import click

from crmint_commands.utils import constants
from crmint_commands.utils import database
from crmint_commands.utils import shared


@click.group()
def cli():
  """CRMint Local Dev CLI"""
  pass

####################### SETUP #######################

CONFIG_FILES = [
    ("backends/instance/config.py.example", "backends/instance/config.py"),
    ("backends/gae_dev_ibackend.yaml.example", "backends/gae_dev_ibackend.yaml"),
    ("backends/gae_dev_jbackend.yaml.example", "backends/gae_dev_jbackend.yaml"),
    ("backends/data/app.json.example", "backends/data/app.json"),
    ("backends/data/service-account.json.example", "backends/data/service-account.json")
]


def _create_config_file(example_path, dest):
  if not os.path.exists(dest):
    copyfile(example_path, dest)


def _create_all_configs():
  for config in CONFIG_FILES:
    full_src_path = os.path.join(constants.PROJECT_DIR, config[0])
    full_dest_path = os.path.join(constants.PROJECT_DIR, config[1])
    _create_config_file(full_src_path, full_dest_path)


@cli.command('setup')
def setup():
  """Setup DB and config files required for local development."""
  click.echo("Setup in progress...")
  try:
    components = [database.create_database, _create_all_configs,
                  shared.install_requirements]
    with click.progressbar(components) as progress_bar:
      for component in progress_bar:
        component()
  except Exception as exception:
    click.echo("Setup failed: {}".format(exception))
    exit(1)


####################### RUN #######################


@cli.group()
def run():
  """Do local development tasks."""
  pass


@run.command('frontend')
def run_frontend():
  """Run frontend services
  """
  frontend = """
  export PYTHONPATH="lib"
  npm install
  node_modules/@angular/cli/bin/ng serve"""
  click.echo("Running frontend...")
  try:
    proc = subprocess.Popen(frontend, cwd=constants.FRONTEND_DIR,
                            shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.stdout.readline()
    click.echo("Server is listening on localhost:4200, open your browser on http://localhost:4200/")
    proc.communicate()
  except KeyboardInterrupt:
    proc.kill()



@run.command('backend')
@click.argument("gcp_app_id")
def run_backend(gcp_app_id):
  """Run backend or frontend services\n
  ARGUMENT: GCP App ID
  """
  run_command = """export PYTHONPATH="lib"
      dev_appserver.py \
        --enable_sendmail=yes \
        --enable_console=yes \
        --env_var APPLICATION_ID={} \
        gae_dev_ibackend.yaml gae_dev_jbackend.yaml
      """.format(gcp_app_id)
  click.echo("Running backend...")
  try:
    proc = subprocess.Popen(run_command, cwd=constants.BACKENDS_DIR,
                            shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    click.echo("Starting module \"api-service\" running at: http://localhost:8080")
    click.echo("Starting module \"job-service\" running at: http://localhost:8081")
    click.echo("Starting admin server at: http://localhost:8000")
    proc.communicate()
  except KeyboardInterrupt:
    proc.kill()


####################### DO ########################


@cli.group()
def do():
  """Do local development tasks."""
  pass


@do.command('requirements')
def do_requirements():
  """Install required Python packages."""
  do_req = """
  pip install -r ibackend/requirements.txt -t lib
  pip install -r jbackend/requirements.txt -t lib
  pip install "sphinx==1.7.2" "sphinx-autobuild==0.7.1"
  """
  click.echo("Doing requirements...")
  proc = subprocess.Popen(do_req, cwd=constants.BACKENDS_DIR,
                          shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  proc.communicate()


@do.command('add_migration')
@click.option('--args')
def do_add_migration(args):
  """Create a new DB migration."""
  if not args:
    args = ""
  add_migration = """
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db revision -m "{}"
  """.format(args)
  click.echo("Adding migration...")
  proc = subprocess.Popen(add_migration, cwd=constants.BACKENDS_DIR,
                          shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  click.echo(proc.stdout.readline())
  proc.communicate()


@do.command('migrations')
def do_migrations():
  """Run new DB migrations."""
  migrations_command = """
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db upgrade"
  """
  click.echo("Running new DB migrations...", nl=False)
  proc = subprocess.Popen(migrations_command, cwd=constants.BACKENDS_DIR,
                          shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  proc.communicate()
  click.echo("\rDone.                    ")


@do.command('seeds')
def do_seeds():
  """Run DB seeds script."""
  seeds_command = """
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db_seeds
  """
  click.echo("Running DB seeds script...", nl=False)
  proc = subprocess.Popen(seeds_command, cwd=constants.BACKENDS_DIR,
                          shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  proc.communicate()
  click.echo("\rDone.                    ")


@do.command('reset')
def do_reset():
  """Reset jobs and pipelines to status 'idle'"""
  reset_command = """
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask reset_pipelines
  """
  click.echo("Resetting...", nl=False)
  proc = subprocess.Popen(reset_command, cwd=constants.BACKENDS_DIR,
                          shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  proc.communicate()
  click.echo("\rDone.                    ")


@cli.command('console')
def console():
  """Run shell console for backend."""
  console_command = """
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask shell
  """
  try:
    click.echo("Running shell console for backend...", nl=False)
    proc = subprocess.Popen(console_command, cwd=constants.BACKENDS_DIR,
                            shell=True)
    proc.wait()
  except KeyboardInterrupt:
    proc.kill()
    click.echo("[w] You will need to reset your shell.")

@cli.command('dbconsole')
def dbconsole():
  """Run DB console for development environment."""
  click.echo("Running DB console for development environment (with default values- crmintapp)...",
             nl=False)
  try:
    proc = subprocess.Popen("mysql --user=crmintapp --password=crmintapp crmintapp",
                            cwd=constants.BACKENDS_DIR,
                            shell=True)
    proc.wait()
  except KeyboardInterrupt:
    proc.kill()