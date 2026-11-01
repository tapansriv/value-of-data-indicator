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
    n.name_pcode_nf IN ('A3524', 'C4532', 'G6526', 'K1524', 'N4252', 'P3623', 'P6152', 'R2631', 'T6526')
  )
  AND (
    ci.note IN ('(executive producer)', '(voice)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director', 'producer')
  )
  AND (
    it1.id IN ('22')
  )
