# Kubernetes Deployment Guide

Deploy your PQC Secure Transfer System on Kubernetes for enterprise-grade container orchestration with full control and scalability.

## 🎯 Why Kubernetes?

- **Enterprise Scale**: Handle thousands of concurrent connections
- **High Availability**: Multi-zone deployments with automatic failover
- **Advanced Networking**: Service mesh, ingress controllers, network policies
- **Resource Management**: Fine-grained CPU/memory allocation and limits
- **Ecosystem**: Rich ecosystem of tools and operators

## 📋 Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.x installed
- Container registry access

## 🚀 Quick Deployment with Helm

### Step 1: Create Helm Chart

```bash
# Create Helm chart structure
mkdir -p k8s/pqc-secure-transfer/templates
cd k8s/pqc-secure-transfer
```

Create `Chart.yaml`:

```yaml
apiVersion: v2
name: pqc-secure-transfer
description: Post-Quantum Cryptography Secure Transfer System
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - post-quantum
  - cryptography
  - federated-learning
  - secure-transfer
maintainers:
  - name: PQC Team
    email: team@pqc-secure-transfer.com
```

Create `values.yaml`:

```yaml
# Default values for pqc-secure-transfer
replicaCount: 3

image:
  repository: pqc-secure-transfer
  pullPolicy: IfNotPresent
  tag: "latest"

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext:
  fsGroup: 2000

securityContext:
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000

service:
  type: ClusterIP
  port: 8765

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/websocket-services: "pqc-secure-transfer"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
  hosts:
    - host: pqc.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: pqc-tls
      hosts:
        - pqc.yourdomain.com

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - pqc-secure-transfer
        topologyKey: kubernetes.io/hostname

persistence:
  enabled: true
  storageClass: "fast-ssd"
  accessMode: ReadWriteMany
  size: 100Gi

config:
  pqcAlgorithm: "Kyber768"
  streamChunkSize: "4194304"
  useAesNi: "true"
  logLevel: "INFO"

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s

networkPolicy:
  enabled: true
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
      ports:
      - protocol: TCP
        port: 8765
```

### Step 2: Create Kubernetes Manifests

Create `templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "pqc-secure-transfer.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "pqc-secure-transfer.selectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "pqc-secure-transfer.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8765
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          env:
            - name: PQC_ALGORITHM
              valueFrom:
                configMapKeyRef:
                  name: {{ include "pqc-secure-transfer.fullname" . }}-config
                  key: pqc-algorithm
            - name: STREAM_CHUNK_SIZE
              valueFrom:
                configMapKeyRef:
                  name: {{ include "pqc-secure-transfer.fullname" . }}-config
                  key: stream-chunk-size
            - name: PQC_KEY_STORE_PATH
              value: "/app/keys"
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: {{ include "pqc-secure-transfer.fullname" . }}-config
                  key: log-level
          volumeMounts:
            - name: keys-storage
              mountPath: /app/keys
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: keys-storage
          {{- if .Values.persistence.enabled }}
          persistentVolumeClaim:
            claimName: {{ include "pqc-secure-transfer.fullname" . }}-keys
          {{- else }}
          emptyDir: {}
          {{- end }}
        - name: tmp
          emptyDir: {}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

Create `templates/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "pqc-secure-transfer.selectorLabels" . | nindent 4 }}
```

Create `templates/ingress.yaml`:

```yaml
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "pqc-secure-transfer.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
```

Create `templates/hpa.yaml`:

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "pqc-secure-transfer.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
{{- end }}
```

### Step 3: Deploy with Helm

```bash
# Add your container registry
helm upgrade --install pqc-secure-transfer ./k8s/pqc-secure-transfer \
  --set image.repository=your-registry/pqc-secure-transfer \
  --set image.tag=latest \
  --set ingress.hosts[0].host=pqc.yourdomain.com \
  --namespace pqc-system \
  --create-namespace
```

## 🔧 Advanced Kubernetes Features

### Multi-Zone Deployment

```yaml
# values-production.yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app.kubernetes.io/name
          operator: In
          values:
          - pqc-secure-transfer
      topologyKey: topology.kubernetes.io/zone

nodeSelector:
  node.kubernetes.io/instance-type: "c5.2xlarge"

tolerations:
- key: "dedicated"
  operator: "Equal"
  value: "pqc-workload"
  effect: "NoSchedule"
```

### Service Mesh with Istio

Create `templates/virtualservice.yaml`:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
spec:
  hosts:
  - pqc.yourdomain.com
  gateways:
  - pqc-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: {{ include "pqc-secure-transfer.fullname" . }}
        port:
          number: 8765
    timeout: 3600s
    websocketUpgrade: true
```

Create `templates/destinationrule.yaml`:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
spec:
  host: {{ include "pqc-secure-transfer.fullname" . }}
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-client-id"
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
    circuitBreaker:
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 30s
```

### Network Policies

Create `templates/networkpolicy.yaml`:

```yaml
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "pqc-secure-transfer.selectorLabels" . | nindent 6 }}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  {{- range .Values.networkPolicy.ingress }}
  - from:
    {{- range .from }}
    - {{ . | toYaml | nindent 6 }}
    {{- end }}
    ports:
    {{- range .ports }}
    - protocol: {{ .protocol }}
      port: {{ .port }}
    {{- end }}
  {{- end }}
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
{{- end }}
```

## 💾 Persistent Storage Solutions

### High-Performance Storage with CSI

```yaml
# templates/storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pqc-fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

### Shared Storage with NFS

```yaml
# templates/pvc.yaml
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}-keys
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  accessModes:
    - {{ .Values.persistence.accessMode }}
  storageClassName: {{ .Values.persistence.storageClass }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
{{- end }}
```

## 📊 Monitoring and Observability

### Prometheus Monitoring

Create `templates/servicemonitor.yaml`:

```yaml
{{- if and .Values.monitoring.enabled .Values.monitoring.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "pqc-secure-transfer.selectorLabels" . | nindent 6 }}
  endpoints:
  - port: http
    interval: {{ .Values.monitoring.serviceMonitor.interval }}
    path: /metrics
    honorLabels: true
{{- end }}
```

### Grafana Dashboard

Create `monitoring/grafana-dashboard.json`:

```json
{
  "dashboard": {
    "id": null,
    "title": "PQC Secure Transfer",
    "tags": ["pqc", "secure-transfer"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"pqc-secure-transfer\"}[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Transfer Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(pqc_bytes_transferred_total[5m])",
            "legendFormat": "Bytes/sec"
          }
        ]
      },
      {
        "title": "Active Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pqc_active_connections",
            "legendFormat": "Connections"
          }
        ]
      }
    ]
  }
}
```

### Jaeger Tracing

```yaml
# Add to deployment.yaml
env:
- name: JAEGER_AGENT_HOST
  value: "jaeger-agent.tracing.svc.cluster.local"
- name: JAEGER_AGENT_PORT
  value: "6831"
- name: JAEGER_SERVICE_NAME
  value: "pqc-secure-transfer"
```

## 🔐 Security Hardening

### Pod Security Standards

```yaml
# templates/podsecuritypolicy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### RBAC Configuration

```yaml
# templates/rbac.yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "pqc-secure-transfer.serviceAccountName" . }}
  labels:
    {{- include "pqc-secure-transfer.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: {{ include "pqc-secure-transfer.fullname" . }}
subjects:
- kind: ServiceAccount
  name: {{ include "pqc-secure-transfer.serviceAccountName" . }}
  namespace: {{ .Release.Namespace }}
{{- end }}
```

## 🚀 GitOps Deployment with ArgoCD

### ArgoCD Application

Create `argocd/application.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: pqc-secure-transfer
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/gayatrigosavi2424/pqc-secure-transfer
    targetRevision: main
    path: k8s/pqc-secure-transfer
    helm:
      valueFiles:
      - values-production.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: pqc-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

### Multi-Environment Setup

```yaml
# argocd/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: pqc-environments
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/gayatrigosavi2424/pqc-secure-transfer
    targetRevision: main
    path: argocd/environments
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## 💰 Cost Optimization

### Vertical Pod Autoscaling

```yaml
# templates/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: {{ include "pqc-secure-transfer.fullname" . }}-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "pqc-secure-transfer.fullname" . }}
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: {{ .Chart.Name }}
      maxAllowed:
        cpu: 4
        memory: 8Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

### Spot Instance Support

```yaml
# values-spot.yaml
nodeSelector:
  karpenter.sh/capacity-type: "spot"

tolerations:
- key: "karpenter.sh/capacity-type"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"

affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
```

## 🧪 Testing and Validation

### Chaos Engineering with Chaos Mesh

```yaml
# chaos/pod-kill.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pqc-pod-kill
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
    - pqc-system
    labelSelectors:
      app.kubernetes.io/name: pqc-secure-transfer
  scheduler:
    cron: "0 */6 * * *"  # Every 6 hours
```

### Load Testing with K6

```javascript
// k6-test.js
import ws from 'k6/ws';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  const url = 'ws://pqc.yourdomain.com/ws';
  const response = ws.connect(url, function (socket) {
    socket.on('open', function open() {
      console.log('connected');
      socket.send('test message');
    });

    socket.on('message', function (message) {
      console.log(`Received message: ${message}`);
    });

    socket.on('close', function close() {
      console.log('disconnected');
    });
  });

  check(response, { 'status is 101': (r) => r && r.status === 101 });
}
```

Run with:
```bash
kubectl run k6-test --image=grafana/k6:latest --rm -it -- run - < k6-test.js
```

## 🚀 Production Deployment Script

Create `deploy-k8s-production.sh`:

```bash
#!/bin/bash

# Configuration
NAMESPACE="pqc-system"
RELEASE_NAME="pqc-secure-transfer"
CHART_PATH="./k8s/pqc-secure-transfer"
DOMAIN="pqc.yourdomain.com"
IMAGE_TAG=${1:-latest}

echo "🚀 Deploying PQC Secure Transfer to Kubernetes..."

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Install cert-manager if not exists
if ! kubectl get crd certificates.cert-manager.io > /dev/null 2>&1; then
    echo "Installing cert-manager..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager -n cert-manager
fi

# Install ingress-nginx if not exists
if ! kubectl get namespace ingress-nginx > /dev/null 2>&1; then
    echo "Installing ingress-nginx..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
fi

# Deploy with Helm
helm upgrade --install $RELEASE_NAME $CHART_PATH \
    --namespace $NAMESPACE \
    --set image.tag=$IMAGE_TAG \
    --set ingress.hosts[0].host=$DOMAIN \
    --set ingress.tls[0].secretName=pqc-tls \
    --set ingress.tls[0].hosts[0]=$DOMAIN \
    --set autoscaling.enabled=true \
    --set autoscaling.minReplicas=3 \
    --set autoscaling.maxReplicas=20 \
    --set resources.requests.cpu=1000m \
    --set resources.requests.memory=2Gi \
    --set resources.limits.cpu=2000m \
    --set resources.limits.memory=4Gi \
    --wait --timeout=600s

# Wait for deployment
kubectl rollout status deployment/$RELEASE_NAME -n $NAMESPACE

# Get service URL
EXTERNAL_IP=$(kubectl get ingress $RELEASE_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "✅ Deployment complete!"
echo "🔗 Service URL: https://$DOMAIN"
echo "📊 Monitor with: kubectl get pods -n $NAMESPACE -w"
echo "📝 Logs: kubectl logs -f deployment/$RELEASE_NAME -n $NAMESPACE"
echo "🧪 Test with: python examples/client.py --server wss://$DOMAIN --create-test 10"
```

Run with:
```bash
chmod +x deploy-k8s-production.sh
./deploy-k8s-production.sh v1.0.0
```

Your PQC Secure Transfer System is now running on Kubernetes with enterprise-grade scalability, security, and observability! 🚀

This completes the comprehensive cloud deployment guide covering all major platforms and deployment methods.