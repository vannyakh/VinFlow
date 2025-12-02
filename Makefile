.PHONY: makemessages compilemessages

makemessages:
	django-admin makemessages -l en -l km --ignore=venv --ignore=.venv

compilemessages:
	django-admin compilemessages

