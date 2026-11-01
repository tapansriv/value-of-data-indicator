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
    n.name_pcode_nf IN ('A4253', 'B2632', 'C342', 'E3532', 'H4142', 'J2563', 'K5321', 'P3625', 'P6121', 'R2425', 'R2525', 'R2632', 'S3126', 'S3616', 'T25', 'T5231')
  )
  AND (
    ci.note IN ('(credit only)', '(executive producer) (uncredited)', '(location manager)', '(producer)', '(production coordinator)', '(senior coordinating producer)', '(uncredited)', '(voice: Japanese version)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
