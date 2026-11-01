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
    n.gender IN ('m') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A4563', 'A5236', 'B6162', 'C5362', 'C652', 'M326', 'M4362', 'N2532', 'R263', 'S1235', 'T5623')
  )
  AND (
    ci.note IN ('(archive footage)', '(first assistant accountant) (uncredited)', '(head writer script)', '(idea)', '(producer)', '(production accountant)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
