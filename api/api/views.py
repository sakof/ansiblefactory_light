from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import mixins
from rest_framework import generics
from rest_framework import status
import ansiblefactory

class RunView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        host = request.data['host']
        playbook = request.data['playbook']
        playbook_exec_return = ansiblefactory.execute_playbook(playbook,host)
        logfile_path = ansiblefactory.log_results(playbook_exec_return['results'], host)
        logfile_upload_return = ansiblefactory.execute_playbook('ansiblefactory/uploadlogs.yml', host, logfile=logfile_path)
        return Response(playbook_exec_return,status=status.HTTP_200_OK)
