
from django.shortcuts import get_object_or_404

from server.models import Project
from server.serializers import LabelSerializer
data={'text': '啊a', 'shortcut': None, 'background_color': '#209cee', 'text_color': '#ffffff'}
ls=LabelSerializer(data=data)
ls.is_valid()
project = get_object_or_404(Project, pk=48)
ls.save(project=project)