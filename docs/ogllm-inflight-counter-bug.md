# OpenGateLLM - Bug potentiel : fuite du compteur inflight Redis

> **Date** : 2026-02-26
> **Statut** : Non corrigé (projet externe)
> **Impact** : Dégradation progressive pouvant mener à des erreurs 503 permanentes sur un provider VLLM
> **Fichiers concernés (OGLLM)** :
> - `api/utils/redis.py`
> - `api/clients/model/_basemodelprovider.py`

## Contexte

OpenGateLLM maintient un compteur Redis par provider VLLM (`ogl_mg:inflight:<provider_id>`) pour suivre le nombre de requêtes en cours. Ce compteur est incrémenté à chaque requête entrante et décrémenté à la fin du traitement. Il est utilisé par la politique QoS pour rejeter les requêtes (503) quand un provider est surchargé.

## Problème identifié

### Cause racine : `redis_retry` avale les erreurs silencieusement

La fonction `redis_retry` (`api/utils/redis.py`) attrape les exceptions Redis (`ConnectionError`, `TimeoutError`, `RedisError`) et **retourne `None`** après épuisement des tentatives, au lieu de lever une exception.

```python
# api/utils/redis.py - ligne 59
return None  # l'appelant ne sait pas que l'opération a échoué
```

### Conséquence sur `forward_request` (non-streaming, lignes 296-339)

```python
inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{self.id}"
try:
    await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
    # ... requête HTTP ...
finally:
    await redis_retry(redis_client.decr, name=inflight_key, max_retries=2)
```

Si le `incr` réussit (compteur = N+1) mais que le `decr` échoue après 2 retries, `redis_retry` retourne `None` sans erreur. Le compteur **reste gonflé à N+1 indéfiniment** (pas de TTL sur ces clés).

### Conséquence sur `forward_stream` (streaming, lignes 396-475)

```python
try:
    await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
    inflight_incremented = True   # ← exécuté même si redis_retry a retourné None
except Exception:
    logger.error(...)             # ← dead code pour les erreurs Redis
```

Double problème :
1. Le `except Exception` ne capture jamais les erreurs Redis (elles sont avalées par `redis_retry`).
2. `inflight_incremented` est mis à `True` même quand l'`incr` a échoué. Le `decr` dans le `finally` peut alors **faire passer le compteur en négatif**.

### Scénario de dérive

Chaque `decr` raté (même 1 sur 1000 requêtes) augmente le compteur d'un cran permanent. Quand il dépasse la limite QoS, le provider VLLM est marqué "too busy" et **toutes les requêtes renvoient 503**.

## Corrections proposées

### 1. Vérifier le retour de `redis_retry` avant de marquer le compteur

Dans les deux méthodes (`forward_request` et `forward_stream`), conditionner `inflight_incremented` au résultat réel :

```python
result = await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
inflight_incremented = result is not None
```

Et ne décrémenter que si l'incrément a réellement eu lieu :

```python
finally:
    if inflight_incremented:
        await redis_retry(redis_client.decr, name=inflight_key, max_retries=2)
```

### 2. Ajouter un paramètre `raise_on_failure` à `redis_retry`

Pour permettre aux appelants de choisir entre le comportement silencieux (rétrocompatible) et un comportement qui lève l'exception :

```python
async def redis_retry[T](
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    backoff_base: float = 0.1,
    backoff_multiplier: float = 2.0,
    raise_on_failure: bool = False,
    **kwargs,
) -> T | None:
    # ... logique existante ...

    if raise_on_failure and last_exception is not None:
        raise last_exception

    return None
```

### 3. Ajouter un TTL comme filet de sécurité

Un crash du process (OOM kill, restart) avant le `finally` laissera le compteur gonflé. Un TTL permet un "self-healing" :

```python
result = await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
if result is not None:
    inflight_incremented = True
    await redis_retry(redis_client.expire, name=inflight_key, time=300, max_retries=1)
```

Le TTL (5 min) est réinitialisé à chaque `incr`, donc tant qu'il y a du trafic la clé persiste. Si le trafic s'arrête, le compteur se remet à zéro automatiquement.

## Vérification immédiate

Pour diagnostiquer si le problème est déjà en cours en production, exécuter sur la machine Redis connectée à OGLLM :

```bash
# Lister tous les compteurs inflight
redis-cli KEYS "ogl_mg:inflight:*"

# Vérifier la valeur de chaque compteur (doit être 0 ou proche de 0 si pas de trafic)
redis-cli MGET $(redis-cli KEYS "ogl_mg:inflight:*" | tr '\n' ' ')

# Vérifier qu'il n'y a pas de TTL (confirmera l'absence de filet de sécurité)
redis-cli TTL "ogl_mg:inflight:<provider_id>"
```

Si un compteur affiche une valeur élevée alors qu'il n'y a pas de trafic, le reset manuel est :

```bash
redis-cli SET "ogl_mg:inflight:<provider_id>" 0
```
