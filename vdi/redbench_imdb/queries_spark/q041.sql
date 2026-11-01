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
    n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A2324', 'A6362', 'B5252', 'D2525', 'D5256', 'J165', 'J2', 'J652', 'M3252', 'P3621', 'R2632', 'R2635', 'S2316', 'S635', 'T6232', 'V2352')
  )
  AND (
    ci.note IN ('(creator)', '(executive producer)', '(legal services)', '(producer)', '(production assistant)', '(production secretary)', '(stage manager)', '(writer)', '(written by) (uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
