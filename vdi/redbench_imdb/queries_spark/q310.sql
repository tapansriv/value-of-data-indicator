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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A2524', 'A5126', 'B25', 'C452', 'E352', 'E6214', 'E6242', 'F6231', 'G3236', 'G5346', 'H412', 'J2315', 'J4156', 'J5253', 'L3243', 'L4352', 'L4535', 'M2635', 'N1215', 'S5242', 'T1323', 'V6345')
  )
  AND (
    ci.note IN ('(producer)', '(voice)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'producer')
  )
  AND (
    it1.id IN ('22')
  )
