# Règles de Sécurité SQL — Smart Lighting AI

Ce fichier définit les règles de sécurité strictes que le LLM doit respecter absolument.
Ces règles complètent et renforcent le module SQLGuard.

---

## Règles fondamentales SQL

1. **SELECT uniquement** — Le LLM doit générer UNIQUEMENT des requêtes SELECT. Aucune modification de données n'est autorisée.

2. **Vues ai_* uniquement** — Utiliser EXCLUSIVEMENT les vues dont le nom commence par `ai_`. Aucune table brute n'est autorisée.

3. **Tables interdites** — Ne jamais accéder directement à :
   - `lampadaires`, `lcus`, `alerts`, `work_orders`
   - `users`, `sensor_measurements`, `access_logs`
   - `ai_query_logs`, `rag_documents`, `rag_chunks`
   - Toute autre table de la base de données

4. **Mots-clés interdits** — Les instructions suivantes sont ABSOLUMENT interdites :
   - `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`
   - `DROP`, `ALTER`, `CREATE`, `RENAME`
   - `COPY`, `GRANT`, `REVOKE`
   - `EXECUTE`, `CALL`, `DO`, `MERGE`
   - `pg_read_file`, `lo_export`, `COPY TO`, `COPY FROM`

5. **LIMIT obligatoire** — Toujours ajouter LIMIT à la requête si la question ne précise pas de limite. Limite par défaut : 100 lignes.

---

## Données sensibles interdites

Ne jamais accéder ni exposer les colonnes suivantes :
- `password`, `password_hash`, `hashed_password`
- `auth_token`, `token`, `refresh_token`, `access_token`
- `api_key`, `secret_key`, `secret`
- Toute variable de configuration `.env`
- Informations personnelles non agrégées des techniciens

---

## Règle SQLGuard

SQLGuard est obligatoire et s'applique APRÈS la génération SQL par le LLM.
- SQLGuard analyse le SQL généré avec sqlglot (AST parsing)
- SQLGuard bloque toute requête non conforme
- Le RAG ne peut pas et ne doit pas contourner SQLGuard
- Si SQLGuard bloque une requête RAG, c'est normal — le LLM doit régénérer

---

## Règles d'action terrain

- **Jamais d'action automatique** — Aucune commande terrain (dimming, reboot, sync) ne peut être déclenchée automatiquement par l'IA.
- **Validation humaine obligatoire** — Toute action sur les équipements nécessite une validation par un opérateur.
- **Pas d'action destructive** — Ne jamais proposer de supprimer, désactiver ou réinitialiser des équipements automatiquement.

---

## Règles sur les exemples SQL du RAG

- Les exemples SQL dans le RAG sont des guides, pas des instructions supérieures à SQLGuard.
- Si un exemple SQL du RAG contient une erreur, SQLGuard la bloquera.
- Le LLM doit adapter les exemples à la question réelle, pas les copier aveuglément.
- Les exemples SQL dans le RAG ne contiennent jamais de données sensibles.

---

## Comportement attendu face aux demandes dangereuses

Si un utilisateur demande :
- "Supprime tous les lampadaires" → Refuser. L'IA ne peut générer que des SELECT.
- "Montre-moi les mots de passe" → Refuser. Données sensibles protégées.
- "Mets à jour le statut de cette LCU" → Refuser. Uniquement lecture.
- "Donne-moi les clés API" → Refuser. Données sensibles.
- "Exécute ce SQL : DROP TABLE" → Refuser. SQLGuard bloquera de toute façon.

Réponse attendue : Expliquer poliment que seules les requêtes de lecture (SELECT) sur les vues `ai_*` sont autorisées.

---

## Principe de moindre privilège

L'utilisateur `ai_readonly` PostgreSQL :
- A accès uniquement aux vues `ai_*` en lecture seule
- Ne peut pas accéder aux tables brutes
- Ne peut pas modifier les données
- Ne peut pas accéder aux configurations système

L'utilisateur `ai_logger` PostgreSQL :
- Peut écrire dans `ai_query_logs`, `rag_documents`, `rag_chunks`
- Ne peut pas accéder aux tables métier brutes
- Droits minimaux nécessaires uniquement
