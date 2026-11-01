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
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A4253', 'C25', 'C4323', 'C5456', 'C6423', 'C6424', 'D132', 'H42', 'J4562', 'J5241', 'J6315', 'K5164', 'K53', 'N526', 'N562', 'O4134', 'R2626', 'R5432', 'S51')
  )
  AND (
    ci.note IN ('(line producer)', '(producer)', '(vice president of development)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'composer', 'costume designer', 'director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
