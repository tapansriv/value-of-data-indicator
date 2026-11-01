SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('f', 'm') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('B6215', 'G4653', 'G5416', 'H4524', 'I5136', 'J5124', 'L1625', 'M2361', 'T5213')
  )
  AND (
    ci.note IN ('(producer)', '(voice: English version)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'costume designer', 'director', 'editor', 'producer', 'writer')
  )
  AND (
    it1.id IN ('26')
  )
