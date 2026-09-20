# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0


from .common import BaseTest

from c7n.provider import get_resource_class, import_resource_classes
from c7n import resources as c7n_resources
from c7n.resources import load_resources
from c7n.resources.resource_map import ResourceMap


class ProviderTest(BaseTest):

    def test_import_resource_classes(self):
        rtypes, missing = import_resource_classes(
            ResourceMap, ('aws.ec2', 'aws.app-elb', 'aws.foobar'))
        self.assertEqual(len(rtypes), 2)
        self.assertEqual([r.type for r in rtypes], ['ec2', 'app-elb'])
        self.assertEqual(missing, ['aws.foobar'])

#    def test_import_resource_classes_wildcard(self):
#        rtypes = import_resource_classes(ResourceMap, ('*',))

    def test_get_resource_class(self):
        with self.assertRaises(KeyError) as ectx:
            get_resource_class('aws.xyz')
        self.assertIn("resource: xyz", str(ectx.exception))

        with self.assertRaises(KeyError) as ectx:
            get_resource_class('xyz.foo')
        self.assertIn("provider: xyz", str(ectx.exception))

        load_resources(('aws.ec2',))
        ec2 = get_resource_class('aws.ec2')
        self.assertEqual(ec2.type, 'ec2')


class LoadAvailableTest(BaseTest):

    def test_missing_provider_is_skipped_quietly(self):
        def fail(provider_types):
            if 'azure' in provider_types:
                raise ImportError("No module named 'c7n_azure'", name='c7n_azure')

        self.patch(c7n_resources, 'load_providers', fail)
        with self.assertNoLogs('c7n.resources', level='WARNING'):
            found = c7n_resources.load_available(resources=False)
        self.assertNotIn('azure', found)
        self.assertIn('aws', found)

    def test_broken_provider_warns_and_is_skipped(self):
        # an installed provider that fails on one of its own dependencies
        # is a real error, but not one worth aborting an aws only run over
        def fail(provider_types):
            if 'gcp' in provider_types:
                raise ImportError("No module named 'googleapiclient'",
                                  name='googleapiclient')

        self.patch(c7n_resources, 'load_providers', fail)
        with self.assertLogs('c7n.resources', level='WARNING') as logs:
            found = c7n_resources.load_available(resources=False)
        self.assertNotIn('gcp', found)
        self.assertIn('aws', found)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('gcp is installed but failed to import', logs.output[0])
        self.assertIn('googleapiclient', logs.output[0])

    def test_import_error_without_name_warns(self):
        def fail(provider_types):
            if 'oci' in provider_types:
                raise ImportError("cannot import name 'thing'")

        self.patch(c7n_resources, 'load_providers', fail)
        with self.assertLogs('c7n.resources', level='WARNING') as logs:
            found = c7n_resources.load_available(resources=False)
        self.assertNotIn('oci', found)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('oci is installed but failed to import', logs.output[0])

    def test_provider_packages_cover_provider_names(self):
        self.assertEqual(
            set(c7n_resources.PROVIDER_NAMES),
            set(c7n_resources.PROVIDER_PACKAGES))
