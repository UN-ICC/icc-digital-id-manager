DOCKER_COMPOSE_FILE = -f docker-compose-local.yml 
# target: help - display callable targets.
help:
	@egrep "^# target:" [Mm]akefile
# target: start - run project
start:
	@docker-compose ${DOCKER_COMPOSE_FILE} up --build --remove-orphans
# target: start_with_db - run project with a DB
start_with_db:
	@docker-compose ${DOCKER_COMPOSE_FILE} --profile db up --build --remove-orphans
# target: startd - run project in daemon mode
startd:
	@docker-compose ${DOCKER_COMPOSE_FILE} up --build -d --remove-orphans
# target: startd_with_db - run project in daemon mode with a DB
startd_with_db:
	@docker-compose ${DOCKER_COMPOSE_FILE} --profile db up --build -d --remove-orphans
# target: stop - stop project
stop:
	@docker-compose ${DOCKER_COMPOSE_FILE} stop
# target: status - docker status
status:
	@docker-compose ${DOCKER_COMPOSE_FILE} ps
# target: restart - stop and run project
restart: stop start
# target: clean - remove stopped containers
clean: stop
	@docker-compose ${DOCKER_COMPOSE_FILE} rm --force
	@find . -name \*.pyc -delete
# target: build - build or rebuild services
build:
	@docker-compose ${DOCKER_COMPOSE_FILE} build
# target: lint - run scripts/linters and then pytest
lint:
	@scripts/linters
# target: black - run black
black:
	@black . $(args)
# target: isort - run isort
isort:
	@isort . $(args)
# target: test - alias for tests
test: tests
# target: tests - pytest
tests:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager pytest -v -p no:warnings --junitxml=/tmp/pytest-report.xml  $(args)
# target: migrate - ./manage.py migrate
migrate:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager python ./manage.py migrate $(args)
# target: cli - run bash in id-manager container
cli:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager bash
# target: shell - ./manage.py shell
shell:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager python ./manage.py shell
# target: tail - logs
tail:
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f
# target: pyclean - remove python tmp files
pyclean:
	find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
# target: managepy - ./make managepy args="createsuperuser --username bob --email bob@example.com"
managepy:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager python ./manage.py $(args)
# target: createsuperuser - ./manage.py createsuperuser
createsuperuser:
	@docker-compose ${DOCKER_COMPOSE_FILE} run --rm id-manager python ./manage.py createsuperuser

.PHONY: help start startd stop status restart clean build lint black isort test tests migrate cli shell tail pyclean managepy createsuperuser