{{- define "jobportal.nom" -}}
{{ .Release.Name }}-{{ .Chart.Name }}
{{- end -}}

{{- define "jobportal.etiquettes" -}}
app: {{ .Release.Name }}
version: {{ .Chart.Version }}
{{- end -}}
