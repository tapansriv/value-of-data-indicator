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
    n.gender IN ('f', 'm')
  )
  AND (
    n.name_pcode_nf IN ('C4625', 'E4546', 'F3624', 'G5432', 'G6231', 'H3653', 'H6323', 'I352', 'J5125', 'L2642', 'L626', 'M2425', 'P3653', 'R2632', 'S3152', 'T534', 'T6523', 'V2346', 'V4656')
  )
  AND (
    ci.note IN ('(executive producer)', '(producer)', '(series creator)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'director', 'producer', 'writer')
  )
  AND (
    it1.id IN ('32')
  )
