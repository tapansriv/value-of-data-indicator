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
    n.name_pcode_nf IN ('B5251', 'B6526', 'C6216', 'C6424', 'D1525', 'D5', 'F1252', 'H2525', 'J5234', 'J5252', 'J5365', 'K232', 'K3625', 'K6461', 'L5626', 'N2421', 'P451', 'R1636', 'R23', 'S5425', 'V2364', 'Y1534', 'Y2153')
  )
  AND (
    ci.note IN ('(TV engineering unit head) (as Carla Enriquez)', '(assistant location manager) (as Paulino Nieva)', '(co-executive producer)', '(co-producer)', '(image designer)', '(line producer)', '(original story)', '(playback supervisor)', '(producer)', '(production accountant)', '(production assistant)', '(promo specialist) (as Kzia Manto)', '(scenario)', '(series producer)', '(stories supervised and based on concepts by)', '(technical director) (as Jhune Castillo)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'director', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
