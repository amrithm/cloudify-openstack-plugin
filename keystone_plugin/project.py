#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from cloudify import ctx
from cloudify.decorators import operation

from openstack_plugin_common import (with_keystone_client,
                                     with_nova_client,
                                     with_cinder_client,
                                     with_neutron_client,
                                     get_resource_id,
                                     use_external_resource,
                                     delete_resource_and_runtime_properties,
                                     validate_resource,
                                     COMMON_RUNTIME_PROPERTIES_KEYS,
                                     OPENSTACK_ID_PROPERTY,
                                     OPENSTACK_TYPE_PROPERTY,
                                     OPENSTACK_NAME_PROPERTY)


PROJECT_OPENSTACK_TYPE = 'tenant'

QUOTA = 'quota'

RUNTIME_PROPERTIES_KEYS = COMMON_RUNTIME_PROPERTIES_KEYS


@operation
@with_keystone_client
@with_nova_client
@with_cinder_client
@with_neutron_client
def create(keystone_client, nova_client, cinder_client,
           neutron_client, **kwargs):
    if use_external_resource(ctx, keystone_client, PROJECT_OPENSTACK_TYPE):
        return

    project_dict = {
        'tenant_name': get_resource_id(ctx, PROJECT_OPENSTACK_TYPE)
    }
    project_dict.update(ctx.node.properties['project'])

    project = keystone_client.tenants.create(**project_dict)

    quota = ctx.node.properties[QUOTA]
    update_quota(project.id, quota, nova_client, cinder_client, neutron_client)

    ctx.instance.runtime_properties[OPENSTACK_ID_PROPERTY] = project.id
    ctx.instance.runtime_properties[OPENSTACK_TYPE_PROPERTY] = \
        PROJECT_OPENSTACK_TYPE
    ctx.instance.runtime_properties[OPENSTACK_NAME_PROPERTY] = project.name


@operation
@with_keystone_client
@with_nova_client
@with_cinder_client
@with_neutron_client
def delete(keystone_client, nova_client, cinder_client,
           neutron_client, **kwargs):
    tenant_id = ctx.instance.runtime_properties[OPENSTACK_ID_PROPERTY]
    quota = ctx.node.properties[QUOTA]
    delete_quota(tenant_id, quota, nova_client, cinder_client, neutron_client)
    delete_resource_and_runtime_properties(ctx, keystone_client,
                                           RUNTIME_PROPERTIES_KEYS) 

@operation
@with_keystone_client
def creation_validation(keystone_client, **kwargs):
    validate_resource(ctx, keystone_client, PROJECT_OPENSTACK_TYPE)


def update_quota(tenant_id, quota, nova_client, cinder_client, neutron_client):
    nova_quota = quota.get('nova')
    if nova_quota:
        new_nova_quota = nova_client.quotas.update(tenant_id=tenant_id,
                                                   **nova_quota)
        ctx.logger.info(
            'Updated nova quota: {0}'.format(new_nova_quota.to_dict()))

    cinder_quota = quota.get('cinder')
    if cinder_quota:
        cinder_client.quotas.update(tenant_id=tenant_id,
                                   **cinder_quota)
        new_cinder_quota = cinder_client.quotas.get(tenant_id=tenant_id)
        ctx.logger.info('Updated cinder quota: {0}'.format(new_cinder_quota))

    neutron_quota = quota.get('neutron')
    if neutron_quota:
        quota_dict = {
            'quota': neutron_quota
        }
        new_neutron_quota = neutron_client.update_quota(tenant_id=tenant_id,
                                                        body=quota_dict)
        ctx.logger.info('Updated neutron quota: {0}'.format(new_neutron_quota))


def delete_quota(tenant_id, quota, nova_client, cinder_client, neutron_client):
    nova_quota = quota.get('nova')
    if nova_quota:
        nova_client.quotas.delete(tenant_id=tenant_id)

    cinder_quota = quota.get('cinder')
    if cinder_quota:
        cinder_client.quotas.delete(tenant_id=tenant_id)

    neutron_quota = quota.get('neutron')
    if neutron_quota:
        neutron_client.delete_quota(tenant_id=tenant_id)
