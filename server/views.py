import csv
import json
from io import TextIOWrapper
import itertools as it
import logging
from django import forms

from django.contrib.auth.views import LoginView as BaseLoginView
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .permissions import SuperUserMixin
from .models import Document, Project, RecommendationHistory,Label
from server.serializers import LabelSerializer,RecommendationHistorySerializer
import spacy
from spacy.tokens import Doc
from django.utils.encoding import escape_uri_path
class WhitespaceTokenizer(object):
    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, text):
        words = text.split(' ')
        # All tokens 'own' a subsequent space character in this tokenizer
        spaces = [True] * len(words)
        return Doc(self.vocab, words=words, spaces=spaces)

nlp = spacy.load("en_core_web_sm")
nlp.tokenizer = WhitespaceTokenizer(nlp.vocab)

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    template_name = 'index.html'


class ProjectView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return project.get_template_name()


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description', 'users')


class ProjectsView(LoginRequiredMixin, CreateView):
    form_class = ProjectForm
    template_name = 'projects.html'


class DatasetView(LoginRequiredMixin, ListView):
    template_name = 'admin/dataset.html'
    paginate_by = 10

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return project.documents.all()


class DictionaryView(LoginRequiredMixin, ListView):
    template_name = 'admin/dictionary.html'
    paginate_by = 10
    queryset = RecommendationHistory.objects.all()

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        self.queryset = self.queryset.filter(project=project, user=self.request.user)
        return self.queryset


class LabelView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/label.html'


class StatsView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/stats.html'


#need fix
class SettingView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/setting.html'


class DataUpload(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/dataset_upload.html'

    class ImportFileError(Exception):
        def __init__(self, message):
            self.message = message

    def extract_metadata_csv(self, row, text_col, header_without_text):
        vals_without_text = [val for i, val in enumerate(row) if i != text_col]
        return json.dumps(dict(zip(header_without_text, vals_without_text)))

    def csv_to_documents(self, project, file, text_key='text'):
        form_data = TextIOWrapper(file, encoding='utf-8')
        reader = csv.reader(form_data)

        maybe_header = next(reader)
        if maybe_header:
            if text_key in maybe_header:
                text_col = maybe_header.index(text_key)
            elif len(maybe_header) == 1:
                reader = it.chain([maybe_header], reader)
                text_col = 0
            else:
                raise DataUpload.ImportFileError("CSV file must have either a title with \"text\" column or have only one column ")

            # header_without_text = [title for i, title in enumerate(maybe_header)
            #                        if i != text_col]

            return (
                Document(
                    # text=" ".join(str(x.text) for x in nlp(row[text_col])),
                    text="".join(row),
                    metadata={},
                    # metadata=self.extract_metadata_csv(row, text_col, header_without_text),
                    project=project
                )
                for row in reader
            )
        else:
            return []

    def extract_metadata_json(self, entry, text_key):
        copy = entry.copy()
        del copy[text_key]
        return json.dumps(copy)

    def json_to_documents(self, project, file, text_key='text'):
        parsed_entries = (json.loads(line) for line in file)

        return (
            Document(text=entry[text_key], metadata=self.extract_metadata_json(entry, text_key), project=project)
            for entry in parsed_entries
        )
    def load_owl_file(self,file):
        import rdflib
        result =[]
        g = rdflib.Graph()
        g.parse(file)
        q = '''SELECT ?class ?classLabel
                    WHERE {
                    ?class rdf:type owl:Class.
                    ?class rdfs:label ?classLabel.
                    }'''
        for a, b in g.query(q):
            result.append(str(b))
        return result
    def add_label(self,data,project):
        ls = LabelSerializer(data=data)
        ls.is_valid()
        ls.save(project=project)
    def owl_to_labels(self,project,file):
        import random
        colorArr = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']
        label_list = self.load_owl_file(file)
        data = { 'shortcut': None,  'text_color': '#ffffff'}
        for label in label_list:
            data['text']=str(label)
            color = ""
            for i in range(6):
                color += colorArr[random.randint(0, 14)]
            data['background_color']="#"+color
            self.add_label(data,project)
    def add_dict(self,data,project,user):
        rs = RecommendationHistorySerializer(data=data)
        rs.is_valid()
        rs.save(project=project, user=user)
    def json_to_dict(self,project,file,user):
        labels =Label.objects.all().filter(project=project.id)
        text_id ={}
        for l in labels:
            text_id[l.text]=l.id
        contents = json.load(file)
        data={}
        for k in contents:
            data['word']=k
            data['label']=text_id[contents[k]]
            self.add_dict(data,project,user)
    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        import_format = request.POST['format']
        try:
            file = request.FILES['file'].file
            documents = []
            if import_format == 'csv':
                documents = self.csv_to_documents(project, file)

            elif import_format == 'json':
                self.json_to_dict(project,file,self.request.user)
                # documents = self.json_to_documents(project, file)
                return HttpResponseRedirect(reverse('dictionary', args=[project.id]))
            elif import_format == 'owl':
                self.owl_to_labels(project,file)
                return HttpResponseRedirect(reverse('label-management', args=[project.id]))
            IMPORT_BATCH_SIZE = 500
            batch_size = IMPORT_BATCH_SIZE
            while True:
                batch = list(it.islice(documents, batch_size))
                if not batch:
                    break

                Document.objects.bulk_create(batch, batch_size=batch_size)
            return HttpResponseRedirect(reverse('dataset', args=[project.id]))
        except DataUpload.ImportFileError as e:
            messages.add_message(request, messages.ERROR, e.message)
            return HttpResponseRedirect(reverse('upload', args=[project.id]))
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, 'Something went wrong')
            return HttpResponseRedirect(reverse('upload', args=[project.id]))


class DataDownload(LoginRequiredMixin, TemplateView):
    template_name = 'admin/dataset_download.html'


class DataDownloadFile(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        user_id = self.request.user.id
        project_id = self.kwargs['project_id']
        project = get_object_or_404(Project, pk=project_id)
        docs = project.get_documents().distinct()
        # print(docs)
        export_format = request.GET.get('format')
        filename = '_'.join(project.name.lower().split())
        try:
            if export_format == 'csv':
                response = self.get_csv(filename, docs, user_id)
            elif export_format == 'json':
                response = self.get_json(filename, docs, user_id)
            return response
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, "Something went wrong")
            return HttpResponseRedirect(reverse('download', args=[project.id]))

    def get_csv(self, filename, docs, user_id):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(escape_uri_path(filename))
        writer = csv.writer(response)
        for d in docs:
            writer.writerows(d.to_csv(user_id))
        return response

    def get_json(self, filename, docs, user_id):
        response = HttpResponse(content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(escape_uri_path(filename))
        for d in docs:
            print(d.to_json())
            dump = json.dumps(d.to_json(), ensure_ascii=False)
            response.write(dump + '\n')  # write each json object end with a newline
        return response


class LoginView(BaseLoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

