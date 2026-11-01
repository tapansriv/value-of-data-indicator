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
    n.name_pcode_nf IN ('B5254', 'B6516', 'C5651', 'C6231', 'C6253', 'E4213', 'J1415', 'K6425', 'L216', 'M6232', 'M6243', 'P4265', 'S3151', 'T4626', 'T525', 'V5256')
  )
  AND (
    ci.note IN ('(co-executive producer)', '(creator)', '(medical advisor)', '(producer)', '(story)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'composer', 'editor', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
